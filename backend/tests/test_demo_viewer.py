"""Demo contract tests: normal RBAC and SQL scope, isolated in-memory data only."""

from contextlib import ExitStack
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON, MetaData, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user, get_effective_permission_codes
from app.dependencies import capabilities
from app.dependencies.database import get_db
from app.main import app
from app.models import (
    AuditEvent, BusinessUnit, Department, Designation, Division, Manufacturer,
    Organization, Permission, Role, RolePermission, User, UserRole,
)
from app.routers import instrument, method, sample, specification, stability_protocol, stability_study, test
from app.seeds import demo_viewer
from app.seeds.demo_viewer import (
    DEMO_VIEWER_ACCESS_SCOPE, DEMO_VIEWER_PERMISSION_CODES, reconcile_demo_viewer,
)
from app.seeds.permissions import PERMISSION_CATALOG
from app.services.audit_service import AuditService
from app.services.organization_scope_service import AccessScope, OrganizationScopeService


APPROVED = {
    "organization.view", "business_unit.view", "division.view", "department.view",
    "designation.view", "location.view", "manufacturer.view", "instrument_type.view",
    "material.view", "instrument.view", "test.view", "method.view", "specification.view",
    "sample.view", "sample_test_result.view", "stability_protocol.view",
    "stability_study.view", "stability_pull.view",
}


def viewer(organization_id, scope=DEMO_VIEWER_ACCESS_SCOPE):
    # Real ORM RBAC graph; authentication alone is replaced by the API fixture.
    role = Role(role_code="DEMO_VIEWER", role_name="Demo Viewer", is_active=True)
    role.role_permissions = [
        RolePermission(is_active=True, permission=Permission(permission_code=code, is_active=True))
        for code in DEMO_VIEWER_PERMISSION_CODES
    ]
    actor = User(id=uuid4(), organization_id=organization_id, is_active=True,
                 force_password_change=False)
    actor.user_roles = [UserRole(role=role, is_active=True, access_scope=scope)]
    return actor


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    # Clone table definitions locally; only the PostgreSQL audit JSONB type needs
    # a SQLite JSON equivalent. Production models/metadata are not altered.
    metadata = MetaData()
    for model in (Organization, BusinessUnit, Division, Department, Designation,
                  Permission, Role, RolePermission, User, UserRole, AuditEvent, Manufacturer):
        model.__table__.to_metadata(metadata)
    metadata.tables["audit_events"].c.changes.type = JSON()
    metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def organizations(db):
    rows = []
    for number in (1, 2):
        org = Organization(organization_code=f"ORG{number}", organization_name=f"Organization {number}")
        db.add(org); db.flush()
        bu = BusinessUnit(organization_id=org.id, business_unit_code=f"BU{number}", business_unit_name="Lab")
        db.add(bu); db.flush()
        division = Division(business_unit_id=bu.id, division_code=f"DIV{number}", division_name="Quality")
        db.add(division); db.flush()
        department = Department(division_id=division.id, department_code=f"DEP{number}", department_name="QC")
        db.add(department); db.flush()
        designation = Designation(department_id=department.id, designation_code=f"DES{number}", designation_name="Analyst")
        maker = Manufacturer(organization_id=org.id, code=f"MAKER{number}", name=f"Maker {number}")
        db.add_all([designation, maker]); db.flush()
        rows.append((org, bu, division, department, designation, maker))
    return rows


@pytest.fixture
def client(db, organizations):
    actor = viewer(organizations[0][0].id)
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_user] = lambda: actor
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as api:
            yield api
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def seed_catalog(db):
    db.add_all([Permission(**item) for item in PERMISSION_CATALOG])
    db.flush()


def test_canonical_permissions_are_exact_and_catalogued():
    assert len(DEMO_VIEWER_PERMISSION_CODES) == 18
    assert set(DEMO_VIEWER_PERMISSION_CODES) == APPROVED
    assert APPROVED <= {item["permission_code"] for item in PERMISSION_CATALOG}
    assert not APPROVED.intersection({"user.view", "role.view", "permission.view", "module.view", "audit.view"})
    assert all(code.endswith(".view") for code in APPROVED)
    actor = viewer(uuid4())
    assert set(get_effective_permission_codes(actor)) == APPROVED
    scope_service = OrganizationScopeService()
    assert all(scope_service.resolve_scope(actor, code) == AccessScope.ORGANIZATION for code in APPROVED)


def test_reconciliation_preserves_role_deactivation_reconciles_mappings_and_is_idempotent(db):
    seed_catalog(db)
    admin = Role(role_code="ADMIN", role_name="Private administrator", is_active=True)
    db.add(admin); db.flush()
    permission = db.query(Permission).filter_by(permission_code="sample.create").one()
    admin_mapping = RolePermission(role_id=admin.id, permission_id=permission.id, is_active=True)
    db.add(admin_mapping)
    role = reconcile_demo_viewer(db)
    db.commit()
    assert role.role_code == "DEMO_VIEWER"
    assert role.role_name == "Demo Viewer"
    assert role.is_active is True
    creation_audit_count = db.query(AuditEvent).count()
    reconcile_demo_viewer(db); db.commit()
    assert role.is_active is True
    assert db.query(AuditEvent).count() == creation_audit_count
    ids = {mapping.id for mapping in role.role_permissions}
    first_mapping = role.role_permissions[0]
    first_mapping.is_active = False
    db.add(RolePermission(role_id=role.id, permission_id=permission.id, is_active=True))
    role.role_name = "Drifted name"
    role.is_active = False
    db.commit()
    role = reconcile_demo_viewer(db)
    db.commit()
    assert role.role_name == "Demo Viewer"
    assert role.is_active is False
    assert {mapping.id for mapping in role.role_permissions} == ids
    assert all(mapping.is_active for mapping in role.role_permissions)
    assert {mapping.permission.permission_code for mapping in role.role_permissions} == APPROVED
    audit_count = db.query(AuditEvent).count()
    reconcile_demo_viewer(db); db.commit()
    assert role.is_active is False
    assert db.query(AuditEvent).count() == audit_count
    assert all(event.source == "OPERATOR" for event in db.query(AuditEvent).all())
    assert admin.role_name == "Private administrator" and admin.is_active
    assert db.get(RolePermission, admin_mapping.id).is_active
    assert db.query(User).count() == db.query(UserRole).count() == 0


@pytest.mark.parametrize("state", ["missing", "inactive"])
def test_reconciliation_fails_closed_before_any_role_write(db, state):
    seed_catalog(db)
    permission = db.query(Permission).filter_by(permission_code="material.view").one()
    if state == "missing":
        db.delete(permission)
    else:
        permission.is_active = False
    db.flush()
    with pytest.raises(ValueError, match="already exist and be active"):
        reconcile_demo_viewer(db)
    assert db.query(Role).count() == db.query(RolePermission).count() == db.query(AuditEvent).count() == 0


def test_reconciliation_and_audit_roll_back_together(db):
    seed_catalog(db); db.commit()
    record_action = AuditService.record_action

    def fail_mapping_audit(service, *args, **kwargs):
        if kwargs["entity_type"] == "RolePermission":
            raise RuntimeError("simulated mapping audit failure")
        return record_action(service, *args, **kwargs)

    with patch.object(AuditService, "record_action", autospec=True, side_effect=fail_mapping_audit):
        with pytest.raises(RuntimeError), db.begin():
            reconcile_demo_viewer(db)
    assert db.query(Role).count() == db.query(RolePermission).count() == db.query(AuditEvent).count() == 0


def test_catalog_discrepancy_stops_reconciliation_before_writes(db):
    with patch.object(demo_viewer, "PERMISSION_CATALOG", []):
        with pytest.raises(ValueError, match="missing catalog permissions"):
            reconcile_demo_viewer(db)
    assert db.query(Role).count() == db.query(AuditEvent).count() == 0


def test_cli_requires_explicit_apply_before_connecting():
    with patch("sys.argv", ["demo_viewer"]), patch.object(demo_viewer, "SessionLocal") as sessions:
        with pytest.raises(SystemExit) as error:
            demo_viewer.main()
    assert error.value.code == 2
    sessions.begin.assert_not_called()


def test_cli_failure_reports_no_database_connection_details(capsys):
    with patch("sys.argv", ["demo_viewer", "--apply"]), patch.object(demo_viewer, "SessionLocal") as sessions:
        sessions.begin.side_effect = RuntimeError("unsafe connection details")
        with pytest.raises(SystemExit) as error:
            demo_viewer.main()
    assert str(error.value) == "DEMO_VIEWER reconciliation failed; transaction rolled back."
    assert "unsafe connection details" not in capsys.readouterr().err


@pytest.mark.parametrize("path,index", [
    ("/organizations/", 0), ("/business-units/", 1), ("/divisions/", 2),
    ("/departments/", 3), ("/designations/", 4), ("/manufacturers", 5),
])
def test_read_lists_are_filtered_in_sql_and_foreign_uuids_are_404(client, organizations, path, index):
    own, foreign = organizations[0][index], organizations[1][index]
    response = client.get(path)
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [str(own.id)]
    assert client.get(f"{path.rstrip('/')}/{own.id}").status_code == 200
    assert client.get(f"{path.rstrip('/')}/{foreign.id}").status_code == 404


@pytest.mark.parametrize("path,index", [
    ("/business-units/organization/", 0), ("/divisions/business-unit/", 1),
    ("/departments/division/", 2), ("/designations/department/", 3),
])
def test_parent_filtered_hierarchy_lists_cannot_leak_other_organizations(client, organizations, path, index):
    response = client.get(f"{path}{organizations[1][index].id}")
    assert response.status_code == 200
    assert response.json() == []


def test_representative_read_families_use_real_permission_dependencies(client):
    sample_id, test_id, study_id = uuid4(), uuid4(), uuid4()
    # Mock only data retrieval/capability availability, not RBAC dependencies.
    cases = [
        (instrument.service, "list_scoped", "/instruments"),
        (test.service, "list", "/tests"),
        (method.method_api_service, "list", "/methods"),
        (specification.specification_api_service, "list", "/specifications"),
        (sample.sample_api_service, "list", "/samples"),
        (sample.sample_test_result_api_service, "list", f"/samples/{sample_id}/tests/{test_id}/results"),
        (stability_protocol.protocols, "list", "/stability-protocols"),
        (stability_study.studies, "list", "/stability-studies"),
        (stability_study.pulls, "list", f"/stability-studies/{study_id}/pulls"),
    ]
    with ExitStack() as stack:
        stack.enter_context(patch.object(capabilities.service, "require_enabled", return_value=None))
        for service, method_name, path in cases:
            mocked = stack.enter_context(patch.object(service, method_name, return_value=[]))
            assert client.get(path).status_code == 200, path
            mocked.assert_called_once()


MUTATIONS = [
    ("POST", "/manufacturers"), ("PUT", "/manufacturers/{id}"), ("DELETE", "/manufacturers/{id}"),
    ("POST", "/samples"), ("PUT", "/samples/{id}"), ("POST", "/samples/{id}/cancel"),
    ("POST", "/samples/{id}/generate-tests"),
    ("POST", "/samples/{id}/tests/{id}/assign"), ("POST", "/samples/{id}/tests/{id}/reassign"),
    ("POST", "/samples/{id}/tests/{id}/unassign"),
    ("POST", "/samples/{id}/tests/{id}/results"), ("PUT", "/samples/{id}/tests/{id}/results/{id}"),
    ("POST", "/samples/{id}/tests/{id}/results/{id}/submit"),
    ("POST", "/samples/{id}/tests/{id}/results/{id}/review"),
    ("POST", "/samples/{id}/tests/{id}/results/{id}/finalize"),
    ("POST", "/stability-studies/{id}/pulls/{id}/mark-pulled"),
    ("POST", "/stability-studies/{id}/pulls/{id}/create-sample"),
    ("POST", "/stability-studies/{id}/pulls/{id}/cancel"),
]


@pytest.mark.parametrize("method,path", MUTATIONS)
def test_mutations_are_denied_before_business_service_execution(client, method, path):
    with ExitStack() as stack:
        services = [stack.enter_context(patch.object(module, attr)) for module, attr in (
            (sample, "sample_api_service"), (sample, "sample_test_assignment_api_service"),
            (sample, "sample_test_result_api_service"), (stability_study, "pulls"),
        )]
        response = client.request(method, path.format(id=uuid4()), json={})
        assert response.status_code == 403
        assert "Permission" in response.json()["detail"]
        assert all(not service.mock_calls for service in services)


@pytest.mark.parametrize("path", [
    "/users/", "/roles/", "/permissions/", "/audit/events", "/security/events",
    "/security/login-history", "/modules", "/qc-dashboard/review-queue",
])
def test_administration_security_and_workflow_queue_are_denied(client, path):
    assert client.get(path).status_code == 403


@pytest.mark.parametrize("part", ["assignment", "role", "mapping", "permission"])
def test_inactive_rbac_chain_cannot_grant_access(client, organizations, part):
    actor = viewer(organizations[0][0].id)
    assignment = actor.user_roles[0]
    if part == "assignment":
        assignment.is_active = False
    elif part == "role":
        assignment.role.is_active = False
    else:
        mapping = next(mapping for mapping in assignment.role.role_permissions
                       if mapping.permission.permission_code == "manufacturer.view")
        if part == "mapping":
            mapping.is_active = False
        else:
            mapping.permission.is_active = False
    app.dependency_overrides[get_current_user] = lambda: actor
    assert client.get("/manufacturers").status_code == 403


def test_lower_scope_hierarchy_reads_do_not_use_unrelated_broader_permission(client, db, organizations):
    sibling = Department(division_id=organizations[0][2].id, department_code="SIBLING", department_name="Other department")
    db.add(sibling); db.flush()
    actor = viewer(organizations[0][0].id, "DEPARTMENT")
    actor.business_unit_id = organizations[0][1].id
    actor.division_id = organizations[0][2].id
    actor.department_id = organizations[0][3].id
    role = Role(role_code="OTHER_READ_ROLE", is_active=True, role_permissions=[
        RolePermission(is_active=True, permission=Permission(permission_code="organization.view", is_active=True))
    ])
    actor.user_roles.append(UserRole(is_active=True, role=role, access_scope="ORGANIZATION"))
    app.dependency_overrides[get_current_user] = lambda: actor
    assert [row["id"] for row in client.get("/departments/").json()] == [str(actor.department_id)]
    assert client.get(f"/departments/{sibling.id}").status_code == 404
