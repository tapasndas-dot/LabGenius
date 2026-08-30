"""Focused Sprint 19B Sample API, scope, audit, and concurrency tests."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.core.exceptions import ResourceNotFoundException, VersionConflictException
from app.dependencies.database import get_db
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.business.sample import Sample
from app.models.organization.business_unit import BusinessUnit
from app.models.organization.department import Department
from app.models.organization.division import Division
from app.services.business.sample_service import SampleAPIService
from tests.test_sprint19a_samples import Sprint19ADatabaseTests


def assignment(permission: str, scope: str):
    mapping = SimpleNamespace(is_active=True, permission=SimpleNamespace(is_active=True, permission_code=permission))
    return SimpleNamespace(is_active=True, access_scope=scope, role=SimpleNamespace(is_active=True, role_permissions=[mapping]))


class Sprint19BTests(Sprint19ADatabaseTests):
    def setUp(self):
        super().setUp(); self.api = SampleAPIService()
        suffix = uuid4().hex[:8]
        self.bu = BusinessUnit(organization_id=self.org.id, business_unit_code=f"B{suffix}", business_unit_name="BU")
        self.sibling_bu = BusinessUnit(organization_id=self.org.id, business_unit_code=f"C{suffix}", business_unit_name="Sibling")
        self.db.add_all([self.bu, self.sibling_bu]); self.db.flush()
        self.division = Division(business_unit_id=self.bu.id, division_code=f"D{suffix}", division_name="Division")
        self.sibling_division = Division(business_unit_id=self.sibling_bu.id, division_code=f"E{suffix}", division_name="Sibling")
        self.db.add_all([self.division, self.sibling_division]); self.db.flush()
        self.department = Department(division_id=self.division.id, department_code=f"F{suffix}", department_name="Department")
        self.sibling_department = Department(division_id=self.sibling_division.id, department_code=f"G{suffix}", department_name="Sibling")
        self.db.add_all([self.department, self.sibling_department]); self.db.flush()

    def tearDown(self):
        app.dependency_overrides.clear(); super().tearDown()

    def actor(self, permission: str, scope="ORGANIZATION"):
        return SimpleNamespace(id=None, organization_id=self.org.id, business_unit_id=self.bu.id, division_id=self.division.id, department_id=self.department.id, force_password_change=False, user_roles=[assignment(permission, scope)])

    def sample(self, number: str, **ownership):
        version = self._basis()[0]
        record = Sample(organization_id=self.org.id, sample_number=number, material_id=self.material.id, specification_version_id=version.id, **ownership)
        self.db.add(record); self.db.flush(); return record

    def test_routes_permissions_and_no_core_lab_gate_or_delete(self):
        client = TestClient(app); actor = self.actor("user.view")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: actor
        self.assertEqual(client.get("/samples").status_code, 403)
        actor.user_roles = [assignment("sample.view", "ORGANIZATION")]
        self.assertEqual(client.get("/samples").status_code, 200)
        self.assertEqual(client.delete(f"/samples/{uuid4()}").status_code, 405)
        paths = app.openapi()["paths"]
        self.assertIn("/samples/{sample_id}/generate-tests", paths)
        self.assertNotIn("CORE_LAB", str(paths["/samples"]))

    def test_sql_scope_self_concealment_and_permission_specific_scope(self):
        rows = [
            self.sample("ORG"), self.sample("BU", business_unit_id=self.bu.id),
            self.sample("DIV", division_id=self.division.id), self.sample("DEP", department_id=self.department.id),
            self.sample("SIB", department_id=self.sibling_department.id),
        ]
        expected = {"ORGANIZATION": 5, "BUSINESS_UNIT": 3, "DIVISION": 2, "DEPARTMENT": 1, "SELF": 0}
        for scope, count in expected.items():
            self.assertEqual(len(self.api.list(self.db, self.actor("sample.view", scope), "sample.view")), count)
        actor = self.actor("sample.view", "SELF"); actor.user_roles.append(assignment("user.view", "ORGANIZATION"))
        self.assertEqual(self.api.list(self.db, actor, "sample.view"), [])
        with self.assertRaises(ResourceNotFoundException): self.api.get(self.db, self.actor("sample.view", "DEPARTMENT"), rows[-1].id, "sample.view")

    def test_create_target_scope_update_concurrency_cancel_generation_and_audit(self):
        version, source, method_version, _ = self._basis()
        values = {"sample_number": " API-1 ", "material_id": self.material.id, "specification_version_id": version.id, "department_id": self.department.id}
        with self.assertRaises(HTTPException): self.api.create(self.db, self.actor("sample.create", "SELF"), "sample.create", values)
        record = self.api.create(self.db, self.actor("sample.create", "DEPARTMENT"), "sample.create", values)
        self.assertEqual((record.organization_id, record.sample_number, record.specification_version_id), (self.org.id, "API-1", version.id))
        with self.assertRaises(HTTPException): self.api.update(self.db, self.actor("sample.update", "DEPARTMENT"), record.id, record.version, "sample.update", {"department_id": self.sibling_department.id})
        record = self.api.update(self.db, self.actor("sample.update", "DEPARTMENT"), record.id, record.version, "sample.update", {"notes": "Updated"})
        generated = self.api.generate_tests(self.db, self.actor("sample.update", "DEPARTMENT"), record.id, "sample.update")
        self.assertEqual(len(generated), 1)
        self.assertEqual((generated[0].specification_test_id, generated[0].test_id, generated[0].method_version_id), (source.id, source.test_id, method_version.id))
        self.assertEqual(len(self.api.generate_tests(self.db, self.actor("sample.update", "DEPARTMENT"), record.id, "sample.update")), 1)
        self.assertEqual(self.api.test(self.db, self.actor("sample.view", "DEPARTMENT"), record.id, generated[0].id, "sample.view").id, generated[0].id)
        with self.assertRaises(ResourceNotFoundException): self.api.test(self.db, self.actor("sample.view", "DEPARTMENT"), record.id, uuid4(), "sample.view")
        record = self.api.cancel(self.db, self.actor("sample.cancel", "DEPARTMENT"), record.id, record.version, "sample.cancel")
        self.assertEqual(record.status, "CANCELLED"); self.assertEqual(len(record.sample_tests), 1)
        with self.assertRaises(VersionConflictException): self.api.cancel(self.db, self.actor("sample.cancel", "DEPARTMENT"), record.id, record.version, "sample.cancel")
        actions = [row.action for row in self.db.query(AuditEvent).filter(AuditEvent.entity_id.in_([record.id, generated[0].id]))]
        self.assertIn("CREATE", actions); self.assertIn("UPDATE", actions); self.assertIn("CANCEL", actions)
        with self.assertRaises(VersionConflictException): self.api.update(self.db, self.actor("sample.update", "DEPARTMENT"), record.id, 1, "sample.update", {"notes": "Stale"})

    def test_audit_failure_rolls_back_create_and_generation(self):
        version = self._basis()[0]; actor = self.actor("sample.create")
        service = SampleAPIService(); service.audit = Mock(); service.audit.record_create.side_effect = RuntimeError("audit failed")
        with self.assertRaises(RuntimeError): service.create(self.db, actor, "sample.create", {"sample_number": "ROLLBACK", "material_id": self.material.id, "specification_version_id": version.id})
        self.assertIsNone(self.db.query(Sample).filter(Sample.sample_number == "ROLLBACK").first())


if __name__ == "__main__": unittest.main()
