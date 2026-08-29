"""Focused Sprint 17B Instrument API, scope, capability, and audit tests."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.exceptions import ResourceNotFoundException, VersionConflictException
from app.database.session import engine
from app.dependencies.database import get_db
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.business import Instrument, InstrumentType
from app.models.module import Module, OrganizationModule
from app.models.organization.business_unit import BusinessUnit
from app.models.organization.department import Department
from app.models.organization.designation import Designation
from app.models.organization.division import Division
from app.models.organization.organization import Organization
from app.models.user.user import User
from app.services.business.instrument_service import InstrumentService


def assignment(permission_code: str, scope: str):
    permission = SimpleNamespace(
        permission_code=permission_code, is_active=True
    )
    mapping = SimpleNamespace(is_active=True, permission=permission)
    role = SimpleNamespace(is_active=True, role_permissions=[mapping])
    return SimpleNamespace(is_active=True, role=role, access_scope=scope)


class Sprint17BTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection)
        suffix = uuid4().hex[:10]
        self.org = Organization(
            organization_code=f"S17B{suffix}", organization_name="Sprint 17B"
        )
        self.other_org = Organization(
            organization_code=f"T17B{suffix}", organization_name="Other"
        )
        self.db.add_all([self.org, self.other_org])
        self.db.flush()
        self.unit = BusinessUnit(
            organization_id=self.org.id, business_unit_code=f"B{suffix}",
            business_unit_name="Unit",
        )
        self.other_unit = BusinessUnit(
            organization_id=self.org.id, business_unit_code=f"C{suffix}",
            business_unit_name="Sibling Unit",
        )
        self.db.add_all([self.unit, self.other_unit])
        self.db.flush()
        self.division = Division(
            business_unit_id=self.unit.id, division_code=f"D{suffix}",
            division_name="Division",
        )
        self.other_division = Division(
            business_unit_id=self.other_unit.id, division_code=f"E{suffix}",
            division_name="Sibling Division",
        )
        self.db.add_all([self.division, self.other_division])
        self.db.flush()
        self.department = Department(
            division_id=self.division.id, department_code=f"F{suffix}",
            department_name="Department",
        )
        self.other_department = Department(
            division_id=self.other_division.id, department_code=f"G{suffix}",
            department_name="Sibling Department",
        )
        self.db.add_all([self.department, self.other_department])
        self.db.flush()
        designation = Designation(
            department_id=self.department.id, designation_code=f"H{suffix}",
            designation_name="Owner",
        )
        self.db.add(designation)
        self.db.flush()
        self.user = User(
            organization_id=self.org.id, business_unit_id=self.unit.id,
            division_id=self.division.id, department_id=self.department.id,
            designation_id=designation.id, employee_code=f"I{suffix}",
            first_name="Instrument", last_name="Owner",
            display_name="Instrument Owner", email=f"{suffix}@example.test",
            username=f"user-{suffix}", password_hash="safe-test-placeholder",
            force_password_change=False,
        )
        self.db.add(self.user)
        self.db.flush()
        self.instrument_type = InstrumentType(
            organization_id=self.org.id, code=f"TYPE{suffix}", name="Type"
        )
        self.other_type = InstrumentType(
            organization_id=self.other_org.id, code=f"OTYPE{suffix}", name="Other"
        )
        self.db.add_all([self.instrument_type, self.other_type])
        self.db.flush()
        self.service = InstrumentService()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        if self.transaction.is_active:
            self.transaction.rollback()
        self.connection.close()

    def actor(self, permission: str, scope: str, **overrides):
        values = dict(
            id=self.user.id, organization_id=self.org.id,
            business_unit_id=self.unit.id, division_id=self.division.id,
            department_id=self.department.id, force_password_change=False,
            user_roles=[assignment(permission, scope)],
        )
        values.update(overrides)
        return SimpleNamespace(**values)

    def instrument(self, code: str, **values):
        record = Instrument(
            organization_id=self.org.id, instrument_type_id=self.instrument_type.id,
            instrument_code=code, instrument_name=code, **values,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def enable_instruments(self):
        module = self.db.query(Module).filter(Module.code == "INSTRUMENTS").one()
        self.db.add(OrganizationModule(
            organization_id=self.org.id, module_id=module.id, is_enabled=True
        ))
        self.db.flush()

    def test_capability_and_permission_are_both_required(self):
        client = TestClient(app)
        actor = self.actor("instrument.view", "ORGANIZATION")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: actor
        self.assertEqual(client.get("/instruments").status_code, 403)
        self.enable_instruments()
        self.assertEqual(client.get("/instruments").status_code, 200)
        actor.user_roles = [assignment("user.view", "ORGANIZATION")]
        self.assertEqual(client.get("/instruments").status_code, 403)

    def test_each_api_operation_requires_its_mapped_permission(self):
        self.enable_instruments()
        record = self.instrument("ROUTE-PERMS")
        client = TestClient(app)
        actor = self.actor("user.view", "ORGANIZATION")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: actor
        requests = (
            ("get", "/instruments", None),
            ("get", f"/instruments/{record.id}", None),
            ("post", "/instruments", {
                "instrument_type_id": str(self.instrument_type.id),
                "instrument_code": "DENIED", "instrument_name": "Denied",
            }),
            ("put", f"/instruments/{record.id}", {
                "version": record.version, "instrument_name": "Denied",
            }),
            ("put", f"/instruments/{record.id}/activate", {"version": record.version}),
            ("put", f"/instruments/{record.id}/deactivate", {"version": record.version}),
            ("delete", f"/instruments/{record.id}", {"version": record.version}),
        )
        for method, path, payload in requests:
            response = client.request(method.upper(), path, json=payload)
            self.assertEqual(response.status_code, 403, (method, path, response.text))

    def test_sql_scope_semantics_and_concealment(self):
        organization_only = self.instrument("ORG")
        unit = self.instrument("UNIT", business_unit_id=self.unit.id)
        division = self.instrument("DIV", division_id=self.division.id)
        department = self.instrument("DEP", department_id=self.department.id)
        sibling = self.instrument("SIB", department_id=self.other_department.id)
        responsible = self.instrument("SELF", responsible_user_id=self.user.id)
        expected = {
            "ORGANIZATION": {"ORG", "UNIT", "DIV", "DEP", "SIB", "SELF"},
            "BUSINESS_UNIT": {"UNIT", "DIV", "DEP"},
            "DIVISION": {"DIV", "DEP"},
            "DEPARTMENT": {"DEP"},
            "SELF": {"SELF"},
        }
        for scope, codes in expected.items():
            actor = self.actor("instrument.view", scope)
            rows = self.service.list_scoped(self.db, actor, "instrument.view")
            self.assertEqual({row.instrument_code for row in rows}, codes)
        self.assertNotIn(organization_only, self.service.list_scoped(
            self.db, self.actor("instrument.view", "SELF"), "instrument.view"
        ))
        with self.assertRaises(ResourceNotFoundException):
            self.service.get_scoped(
                self.db, self.actor("instrument.view", "DEPARTMENT"),
                sibling.id, "instrument.view",
            )
        with self.assertRaises(ResourceNotFoundException):
            self.service.get_scoped(
                self.db, self.actor("instrument.view", "ORGANIZATION"),
                uuid4(), "instrument.view",
            )
        other = Instrument(
            organization_id=self.other_org.id, instrument_type_id=self.other_type.id,
            instrument_code="CROSS", instrument_name="Cross",
        )
        self.db.add(other)
        self.db.flush()
        with self.assertRaises(ResourceNotFoundException):
            self.service.get_scoped(
                self.db, self.actor("instrument.view", "ORGANIZATION"),
                other.id, "instrument.view",
            )

    def test_only_permission_bearing_assignments_contribute_scope(self):
        actor = self.actor("instrument.view", "DEPARTMENT")
        actor.user_roles.append(assignment("user.view", "ORGANIZATION"))
        self.instrument("DEP", department_id=self.department.id)
        self.instrument("SIB", department_id=self.other_department.id)
        rows = self.service.list_scoped(self.db, actor, "instrument.view")
        self.assertEqual([row.instrument_code for row in rows], ["DEP"])
        actor.user_roles.append(assignment("instrument.view", "ORGANIZATION"))
        rows = self.service.list_scoped(self.db, actor, "instrument.view")
        self.assertEqual({row.instrument_code for row in rows}, {"DEP", "SIB"})

    def test_create_and_reassignment_scope_rules(self):
        department_actor = self.actor("instrument.create", "DEPARTMENT")
        values = {
            "instrument_type_id": self.instrument_type.id,
            "instrument_code": "CREATE-DEP", "instrument_name": "Created",
            "department_id": self.department.id,
        }
        created = self.service.create_scoped(self.db, department_actor, values)
        self.assertEqual(created.department_id, self.department.id)
        with self.assertRaises(HTTPException):
            self.service.create_scoped(
                self.db, department_actor,
                {**values, "instrument_code": "OUTSIDE",
                 "department_id": self.other_department.id},
            )
        with self.assertRaises(HTTPException):
            self.service.create_scoped(
                self.db, self.actor("instrument.create", "SELF"),
                {**values, "instrument_code": "SELF-CREATE"},
            )
        created.responsible_user_id = self.user.id
        self.db.flush()
        self_actor = self.actor("instrument.update", "SELF")
        with self.assertRaises(HTTPException):
            self.service.update_scoped(
                self.db, self_actor, created.id, created.version,
                {"department_id": self.other_department.id},
            )

    def test_concurrency_audit_and_active_status_independence(self):
        actor = self.actor("instrument.create", "ORGANIZATION")
        record = self.service.create_scoped(self.db, actor, {
            "instrument_type_id": self.instrument_type.id,
            "instrument_code": "AUDIT", "instrument_name": "Original",
        })
        actor.user_roles = [assignment("instrument.update", "ORGANIZATION")]
        record = self.service.update_scoped(
            self.db, actor, record.id, record.version,
            {"instrument_name": "Updated"},
        )
        record = self.service.set_active_scoped(
            self.db, actor, record.id, record.version, False
        )
        self.assertFalse(record.is_active)
        self.assertEqual(record.status, "AVAILABLE")
        record = self.service.set_active_scoped(
            self.db, actor, record.id, record.version, True
        )
        actor.user_roles = [assignment("instrument.delete", "ORGANIZATION")]
        self.service.delete_scoped(self.db, actor, record.id, record.version)
        events = self.db.query(AuditEvent).filter(
            AuditEvent.entity_type == "Instrument",
            AuditEvent.entity_id == record.id,
        ).order_by(AuditEvent.occurred_at).all()
        self.assertEqual(
            [event.action for event in events],
            ["CREATE", "UPDATE", "DEACTIVATE", "ACTIVATE", "DELETE"],
        )
        update = next(event for event in events if event.action == "UPDATE")
        self.assertEqual(set(update.changes), {"instrument_name", "version"})

    def test_stale_in_scope_conflicts_and_inaccessible_stale_is_concealed(self):
        record = self.instrument("STALE", department_id=self.department.id)
        actor = self.actor("instrument.update", "ORGANIZATION")
        with self.assertRaises(VersionConflictException):
            self.service.update_scoped(
                self.db, actor, record.id, record.version + 1,
                {"instrument_name": "Stale"},
            )

    def test_inaccessible_stale_row_is_concealed_before_version_check(self):
        record = self.instrument("HIDDEN", department_id=self.other_department.id)
        actor = self.actor("instrument.update", "DEPARTMENT")
        with self.assertRaises(ResourceNotFoundException):
            self.service.update_scoped(
                self.db, actor, record.id, record.version + 99,
                {"instrument_name": "Disclose"},
            )

    def test_audit_failure_rolls_back_create(self):
        service = InstrumentService()
        service.audit_service = Mock()
        service.audit_service.record_create.side_effect = RuntimeError("audit failed")
        actor = self.actor("instrument.create", "ORGANIZATION")
        with self.assertRaises(RuntimeError):
            service.create_scoped(self.db, actor, {
                "instrument_type_id": self.instrument_type.id,
                "instrument_code": "ROLLBACK", "instrument_name": "Rollback",
            })
        self.assertIsNone(
            self.db.query(Instrument).filter(Instrument.instrument_code == "ROLLBACK").first()
        )


if __name__ == "__main__":
    unittest.main()
