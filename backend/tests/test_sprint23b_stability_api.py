"""Focused HTTP-boundary tests for Sprint 23B Stability APIs."""
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.dependencies.database import get_db
from app.main import app
from app.models.business.instrument import Instrument, StabilityChamberProfile
from app.models.business.instrument_type import InstrumentType
from app.models.business.material import Material
from app.models.business.stability import StabilityStudy
from app.models.organization.business_unit import BusinessUnit
from app.models.organization.department import Department
from app.models.organization.division import Division
from app.services.business.stability_service import (
    StabilityProtocolConditionService, StabilityProtocolService,
    StabilityProtocolTimepointService, StabilityProtocolVersionService,
)
from tests.test_sprint19a_samples import Sprint19ADatabaseTests


def assignment(permission, scope="ORGANIZATION"):
    mapping = SimpleNamespace(is_active=True, permission=SimpleNamespace(is_active=True, permission_code=permission))
    return SimpleNamespace(is_active=True, access_scope=scope, role=SimpleNamespace(is_active=True, role_permissions=[mapping]))


class Sprint23BStabilityAPITests(Sprint19ADatabaseTests):
    def setUp(self):
        super().setUp()
        suffix = uuid4().hex[:6]
        self.bu = BusinessUnit(organization_id=self.org.id, business_unit_code=f"B{suffix}", business_unit_name="BU")
        self.other_bu = BusinessUnit(organization_id=self.org.id, business_unit_code=f"C{suffix}", business_unit_name="Other BU")
        self.db.add_all([self.bu, self.other_bu]); self.db.flush()
        self.division = Division(business_unit_id=self.bu.id, division_code=f"D{suffix}", division_name="Division")
        self.other_division = Division(business_unit_id=self.other_bu.id, division_code=f"E{suffix}", division_name="Other Division")
        self.db.add_all([self.division, self.other_division]); self.db.flush()
        self.department = Department(division_id=self.division.id, department_code=f"F{suffix}", department_name="Department")
        self.other_department = Department(division_id=self.other_division.id, department_code=f"G{suffix}", department_name="Other Department")
        self.db.add_all([self.department, self.other_department]); self.db.flush()
        self.actor = self.make_actor("stability_protocol.view")
        def override_db():
            session = Session(bind=self.connection, join_transaction_mode="create_savepoint")
            try:
                yield session
            finally:
                session.close()
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: self.actor
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        super().tearDown()

    def make_actor(self, *permissions, scope="ORGANIZATION"):
        return SimpleNamespace(
            id=None, organization_id=self.org.id, business_unit_id=self.bu.id,
            division_id=self.division.id, department_id=self.department.id,
            force_password_change=False,
            user_roles=[assignment(permission, scope) for permission in permissions],
        )

    def use_permissions(self, *permissions, scope="ORGANIZATION"):
        self.actor = self.make_actor(*permissions, scope=scope)

    def create_protocol_tree(self, specification_version=None, *, approve=False):
        actor = self.make_actor("stability_protocol.create", "stability_protocol.update")
        protocols = StabilityProtocolService(); versions = StabilityProtocolVersionService()
        conditions = StabilityProtocolConditionService(); timepoints = StabilityProtocolTimepointService()
        protocol = protocols.create(self.db, actor, {"protocol_code": f"P-{uuid4().hex[:6]}", "protocol_name": "Protocol"})
        version = versions.create(self.db, actor, protocol.id, {"version_number": 1})
        condition = conditions.create(self.db, actor, version.id, {"sequence_number": 1, "condition_code": "LONG", "condition_name": "Long Term"})
        if specification_version:
            timepoint = timepoints.create(self.db, actor, condition.id, {"sequence_number": 1, "label": "Initial", "is_initial": True, "specification_version_id": specification_version.id})
        else:
            timepoint = None
        if approve:
            version = versions.transition(self.db, actor, version.id, version.version, "APPROVED")
        self.db.flush()
        return protocol, version, condition, timepoint

    def test_protocol_http_crud_permissions_cross_org_and_concurrency(self):
        self.use_permissions("user.view")
        self.assertEqual(self.client.get("/stability-protocols").status_code, 403)
        self.use_permissions("stability_protocol.view", "stability_protocol.create", "stability_protocol.update", "stability_protocol.delete")
        created = self.client.post("/stability-protocols", json={"protocol_code": " API-P ", "protocol_name": " API Protocol "})
        self.assertEqual(created.status_code, 201); protocol = created.json()
        self.assertEqual(self.client.get("/stability-protocols").status_code, 200)
        self.assertEqual(self.client.get(f"/stability-protocols/{protocol['id']}").status_code, 200)
        updated = self.client.put(f"/stability-protocols/{protocol['id']}", json={"version": protocol["version"], "description": "Updated"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(self.client.put(f"/stability-protocols/{protocol['id']}", json={"version": protocol["version"], "description": "Stale"}).status_code, 409)
        deactivated = self.client.post(f"/stability-protocols/{protocol['id']}/deactivate", json={"version": updated.json()["version"]})
        self.assertEqual(deactivated.status_code, 200)
        activated = self.client.post(f"/stability-protocols/{protocol['id']}/activate", json={"version": deactivated.json()["version"]})
        self.assertEqual(activated.status_code, 200)
        other = StabilityProtocolService().create(self.db, SimpleNamespace(id=None, organization_id=self.other_org.id), {"protocol_code": "OTHER", "protocol_name": "Other"})
        self.db.flush()
        self.assertEqual(self.client.get(f"/stability-protocols/{other.id}").status_code, 404)
        disposable = self.client.post("/stability-protocols", json={"protocol_code": "DELETE", "protocol_name": "Delete"}).json()
        self.assertEqual(self.client.request("DELETE", f"/stability-protocols/{disposable['id']}", json={"version": disposable["version"]}).status_code, 204)

    def test_nested_protocol_version_condition_and_timepoint_security(self):
        self.use_permissions("stability_protocol.view", "stability_protocol.create", "stability_protocol.update")
        protocol = self.client.post("/stability-protocols", json={"protocol_code": "TREE", "protocol_name": "Tree"}).json()
        version = self.client.post(f"/stability-protocols/{protocol['id']}/versions", json={"version_number": 1}).json()
        self.assertEqual(self.client.get(f"/stability-protocols/{protocol['id']}/versions/{version['id']}").status_code, 200)
        version = self.client.put(f"/stability-protocols/{protocol['id']}/versions/{version['id']}", json={"version": version["version"], "version_label": "One"}).json()
        self.assertEqual(self.client.put(f"/stability-protocols/{protocol['id']}/versions/{version['id']}", json={"version": 1, "description": "Stale"}).status_code, 409)
        condition = self.client.post(f"/stability-protocols/{protocol['id']}/versions/{version['id']}/conditions", json={"sequence_number": 1, "condition_code": "C1", "condition_name": "Condition"}).json()
        conditions_url = f"/stability-protocols/{protocol['id']}/versions/{version['id']}/conditions"
        self.assertEqual(len(self.client.get(conditions_url).json()), 1)
        condition = self.client.put(f"{conditions_url}/{condition['id']}", json={"version": condition["version"], "description": "Updated"}).json()
        specification = self._basis()[0]
        timepoint_url = f"/stability-protocols/{protocol['id']}/versions/{version['id']}/conditions/{condition['id']}/timepoints"
        timepoint = self.client.post(timepoint_url, json={"sequence_number": 1, "label": "Initial", "is_initial": True, "specification_version_id": str(specification.id)}).json()
        self.assertEqual(len(self.client.get(timepoint_url).json()), 1)
        self.assertEqual(self.client.get(f"{timepoint_url}/{timepoint['id']}").status_code, 200)
        self.assertEqual(self.client.get(f"{timepoint_url}/{uuid4()}").status_code, 404)
        other_protocol, other_version, other_condition, _ = self.create_protocol_tree()
        self.assertEqual(self.client.get(f"/stability-protocols/{other_protocol.id}/versions/{version['id']}").status_code, 404)
        wrong = f"/stability-protocols/{other_protocol.id}/versions/{other_version.id}/conditions/{other_condition.id}"
        self.assertEqual(self.client.get(f"{wrong}/timepoints/{timepoint['id']}").status_code, 404)
        disposable_condition = self.client.post(conditions_url, json={"sequence_number": 2, "condition_code": "C2", "condition_name": "Disposable"}).json()
        disposable_url = f"{conditions_url}/{disposable_condition['id']}/timepoints"
        disposable_timepoint = self.client.post(disposable_url, json={"sequence_number": 1, "label": "Month 1", "interval_value": 1, "interval_unit": "MONTH", "specification_version_id": str(specification.id)}).json()
        disposable_timepoint = self.client.put(f"{disposable_url}/{disposable_timepoint['id']}", json={"version": disposable_timepoint["version"], "label": "Month One"}).json()
        self.assertEqual(self.client.request("DELETE", f"{disposable_url}/{disposable_timepoint['id']}", json={"version": disposable_timepoint["version"]}).status_code, 204)
        self.assertEqual(self.client.request("DELETE", f"{conditions_url}/{disposable_condition['id']}", json={"version": disposable_condition["version"]}).status_code, 204)
        draft_specification = self._basis(approved=False)[0]
        self.assertEqual(self.client.post(timepoint_url, json={"sequence_number": 2, "label": "Bad", "interval_value": 1, "interval_unit": "MONTH", "specification_version_id": str(draft_specification.id)}).status_code, 400)
        approved = self.client.post(f"/stability-protocols/{protocol['id']}/versions/{version['id']}/approve", json={"version": version["version"]})
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(self.client.put(f"{timepoint_url}/{timepoint['id']}", json={"version": timepoint["version"], "label": "Late"}).status_code, 400)
        self.assertEqual(self.client.put(f"{conditions_url}/{condition['id']}", json={"version": condition["version"], "condition_name": "Late"}).status_code, 400)
        second = self.client.post(f"/stability-protocols/{protocol['id']}/versions", json={"version_number": 2}).json()
        second = self.client.post(f"/stability-protocols/{protocol['id']}/versions/{second['id']}/approve", json={"version": second["version"]}).json()
        self.assertEqual(self.client.post(f"/stability-protocols/{protocol['id']}/versions/{second['id']}/supersede", json={"version": second["version"]}).status_code, 200)
        self.assertEqual(self.client.post(f"/stability-protocols/{protocol['id']}/versions/{version['id']}/retire", json={"version": approved.json()["version"]}).status_code, 200)

    def test_study_http_scope_self_lifecycle_concurrency_and_material_compatibility(self):
        specification = self._basis()[0]
        _, version, _, _ = self.create_protocol_tree(specification, approve=True)
        self.use_permissions("stability_study.view", "stability_study.create", "stability_study.update", "stability_study.cancel")
        payload = {"study_number": "API-S", "study_name": "Study", "material_id": str(self.material.id), "stability_protocol_version_id": str(version.id), "department_id": str(self.department.id), "start_date": "2026-01-01"}
        created = self.client.post("/stability-studies", json=payload)
        self.assertEqual(created.status_code, 201); study = created.json()
        self.assertEqual(self.client.get("/stability-studies").status_code, 200)
        updated = self.client.put(f"/stability-studies/{study['id']}", json={"version": study["version"], "notes": "Updated"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(self.client.put(f"/stability-studies/{study['id']}", json={"version": study["version"], "notes": "Stale"}).status_code, 409)
        active = self.client.post(f"/stability-studies/{study['id']}/activate", json={"version": updated.json()["version"]})
        self.assertEqual(active.status_code, 200)
        self.assertEqual(self.client.post(f"/stability-studies/{study['id']}/complete", json={"version": active.json()["version"]}).status_code, 200)
        cancelled = self.client.post("/stability-studies", json={**payload, "study_number": "CANCEL"}).json()
        self.assertEqual(self.client.post(f"/stability-studies/{cancelled['id']}/cancel", json={"version": cancelled["version"]}).status_code, 200)
        self.use_permissions("stability_study.view", scope="SELF")
        self.assertEqual(self.client.get("/stability-studies").json(), [])
        self.assertEqual(self.client.get(f"/stability-studies/{study['id']}").status_code, 404)
        self.use_permissions("stability_study.view", scope="DEPARTMENT")
        hidden = StabilityStudy(organization_id=self.org.id, department_id=self.other_department.id, study_number="HIDDEN", study_name="Hidden", material_id=self.material.id, stability_protocol_version_id=version.id)
        self.db.add(hidden); self.db.flush()
        self.assertEqual(self.client.get(f"/stability-studies/{hidden.id}").status_code, 404)
        other_material = Material(organization_id=self.org.id, code=f"X{uuid4().hex[:6]}", name="Other", material_type="OTHER")
        self.db.add(other_material); self.db.flush()
        other_specification = self._basis(material=other_material)[0]
        _, mismatched_version, _, _ = self.create_protocol_tree(other_specification, approve=True)
        self.use_permissions("stability_study.create", "stability_study.update")
        mismatch = self.client.post("/stability-studies", json={**payload, "study_number": "MISMATCH", "stability_protocol_version_id": str(mismatched_version.id)}).json()
        self.assertEqual(self.client.post(f"/stability-studies/{mismatch['id']}/activate", json={"version": mismatch["version"]}).status_code, 400)
        persisted = self.db.get(StabilityStudy, UUID(mismatch["id"])); self.db.refresh(persisted)
        self.assertEqual(persisted.status, "DRAFT")

    def test_study_condition_http_parent_scope_chamber_and_lifecycle_rules(self):
        _, version, condition, _ = self.create_protocol_tree(approve=True)
        instrument_type = InstrumentType(organization_id=self.org.id, code=f"I{uuid4().hex[:6]}", name="Chamber")
        self.db.add(instrument_type); self.db.flush()
        instrument = Instrument(organization_id=self.org.id, instrument_type_id=instrument_type.id, instrument_code=f"I{uuid4().hex[:6]}", instrument_name="Chamber")
        self.db.add(instrument); self.db.flush()
        self.use_permissions("stability_study.view", "stability_study.create", "stability_study.update", "stability_study.cancel")
        payload = {"study_name": "Study", "material_id": str(self.material.id), "stability_protocol_version_id": str(version.id), "department_id": str(self.department.id), "start_date": "2026-01-01"}
        first = self.client.post("/stability-studies", json={**payload, "study_number": "SC-1"}).json()
        second = self.client.post("/stability-studies", json={**payload, "study_number": "SC-2"}).json()
        condition_url = f"/stability-studies/{first['id']}/conditions"
        assignment_payload = {"stability_protocol_condition_id": str(condition.id), "instrument_id": str(instrument.id)}
        self.assertEqual(self.client.post(condition_url, json=assignment_payload).status_code, 400)
        self.db.add(StabilityChamberProfile(instrument_id=instrument.id)); self.db.flush()
        created = self.client.post(condition_url, json=assignment_payload)
        self.assertEqual(created.status_code, 201); study_condition = created.json()
        self.assertEqual(len(self.client.get(condition_url).json()), 1)
        self.assertEqual(self.client.get(f"{condition_url}/{study_condition['id']}").status_code, 200)
        self.assertEqual(self.client.get(f"/stability-studies/{second['id']}/conditions/{study_condition['id']}").status_code, 404)
        disposable = self.client.post(f"/stability-studies/{second['id']}/conditions", json=assignment_payload).json()
        self.assertEqual(self.client.request("DELETE", f"/stability-studies/{second['id']}/conditions/{disposable['id']}", json={"version": disposable["version"]}).status_code, 204)
        updated = self.client.put(f"{condition_url}/{study_condition['id']}", json={"version": study_condition["version"], "notes": "Updated"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(self.client.put(f"{condition_url}/{study_condition['id']}", json={"version": study_condition["version"], "notes": "Stale"}).status_code, 409)
        active = self.client.post(f"/stability-studies/{first['id']}/activate", json={"version": first["version"]}).json()
        self.assertEqual(self.client.request("DELETE", f"{condition_url}/{study_condition['id']}", json={"version": updated.json()["version"]}).status_code, 400)
        completed = self.client.post(f"/stability-studies/{first['id']}/complete", json={"version": active["version"]})
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(self.client.put(f"{condition_url}/{study_condition['id']}", json={"version": updated.json()["version"], "notes": "Late"}).status_code, 400)

    def test_openapi_paths_operation_ids_and_oauth_contract(self):
        schema = app.openapi()
        operations = [operation["operationId"] for path in schema["paths"].values() for operation in path.values() if isinstance(operation, dict) and "operationId" in operation]
        self.assertEqual(len(operations), len(set(operations)))
        self.assertIn("/stability-protocols/{protocol_id}/versions/{version_id}/conditions/{condition_id}/timepoints/{timepoint_id}", schema["paths"])
        self.assertIn("/stability-studies/{study_id}/conditions/{study_condition_id}", schema["paths"])
        self.assertEqual(schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]["password"]["tokenUrl"], "/auth/login")
