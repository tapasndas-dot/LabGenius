"""Focused Sprint 18C API, scope, lifecycle, and audit tests."""

import unittest
from collections import Counter
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.exceptions import ResourceNotFoundException, SecurityConflictException, ValidationException, VersionConflictException
from app.database.session import engine
from app.dependencies.database import get_db
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.business.material import Material
from app.models.business.qc_method import Method, Test
from app.models.organization.organization import Organization
from app.services.audit_service import AuditAction
from app.services.business.qc_api_service import HeaderService, MethodTreeAPIService, SpecificationTreeAPIService
from app.services.business.qc_method_service import MethodService, TestService
from app.services.business.specification_service import SpecificationService
from app.repositories.business import MethodRepository, SpecificationRepository, TestRepository


def assignment(permission, scope):
    mapping = SimpleNamespace(is_active=True, permission=SimpleNamespace(is_active=True, permission_code=permission))
    return SimpleNamespace(is_active=True, access_scope=scope, role=SimpleNamespace(is_active=True, role_permissions=[mapping]))


class Sprint18CAPITests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect(); self.transaction = self.connection.begin(); self.db = Session(bind=self.connection)
        suffix = uuid4().hex[:10].upper()
        self.org = Organization(organization_code=f"C18{suffix}", organization_name="Sprint 18C")
        self.other = Organization(organization_code=f"D18{suffix}", organization_name="Other")
        self.db.add_all([self.org, self.other]); self.db.flush()
        self.material = Material(organization_id=self.org.id, code="MAT", name="Material", material_type="OTHER")
        self.db.add(self.material); self.db.flush()
        self.test_api = HeaderService(TestService(), TestRepository(), "test_code")
        self.method_api = HeaderService(MethodService(), MethodRepository(), "method_code")
        self.spec_api = HeaderService(SpecificationService(), SpecificationRepository(), "specification_code")
        self.methods = MethodTreeAPIService(); self.specs = SpecificationTreeAPIService()

    def tearDown(self):
        app.dependency_overrides.clear(); self.db.close()
        if self.transaction.is_active: self.transaction.rollback()
        self.connection.close()

    def actor(self, permission, scope="ORGANIZATION", org=None):
        return SimpleNamespace(id=None, organization_id=(org or self.org).id, business_unit_id=None, division_id=None, department_id=None, force_password_change=False, user_roles=[assignment(permission, scope)])

    def test_routes_permissions_and_core_lab_has_no_redundant_capability_gate(self):
        client = TestClient(app); actor = self.actor("user.view")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: actor
        for path in ("/tests", "/methods", "/specifications"):
            self.assertEqual(client.get(path).status_code, 403)
        actor.user_roles = [assignment("test.view", "ORGANIZATION")]
        self.assertEqual(client.get("/tests").status_code, 200)
        self.assertNotIn("CORE_LAB", str(app.openapi()["paths"]["/tests"]))

    def test_test_crud_scope_concurrency_status_and_audit(self):
        creator = self.actor("test.create")
        record = self.test_api.create(self.db, creator, "test.create", {"test_code": " assay ", "test_name": "Assay"})
        self.assertEqual(record.test_code, "ASSAY")
        for scope in ("ORGANIZATION", "BUSINESS_UNIT", "DIVISION", "DEPARTMENT"):
            self.assertEqual(len(self.test_api.list(self.db, self.actor("test.view", scope), "test.view")), 1)
        self.assertEqual(self.test_api.list(self.db, self.actor("test.view", "SELF"), "test.view"), [])
        with self.assertRaises(HTTPException): self.test_api.create(self.db, self.actor("test.create", "SELF"), "test.create", {"test_code": "NO", "test_name": "No"})
        with self.assertRaises(ResourceNotFoundException): self.test_api.get(self.db, self.actor("test.view", org=self.other), record.id, "test.view")
        record = self.test_api.update(self.db, self.actor("test.update"), record.id, 1, "test.update", {"test_name": "Updated"})
        record = self.test_api.set_active(self.db, self.actor("test.update"), record.id, record.version, "test.update", False)
        record = self.test_api.set_active(self.db, self.actor("test.update"), record.id, record.version, "test.update", True)
        self.test_api.delete(self.db, self.actor("test.delete"), record.id, record.version, "test.delete")
        actions = [row.action for row in self.db.query(AuditEvent).filter(AuditEvent.entity_id == record.id)]
        self.assertEqual(Counter(actions), Counter(["CREATE", "UPDATE", "DEACTIVATE", "ACTIVATE", "DELETE"]))

    def test_stale_header_update_returns_conflict(self):
        record = self.test_api.create(self.db, self.actor("test.create"), "test.create", {"test_code": "STALE", "test_name": "Stale"})
        record = self.test_api.update(self.db, self.actor("test.update"), record.id, 1, "test.update", {"test_name": "Updated"})
        with self.assertRaises(VersionConflictException): self.test_api.update(self.db, self.actor("test.update"), record.id, 1, "test.update", {"test_name": "Again"})

    def test_permission_specific_scope_does_not_broaden(self):
        self.test_api.create(self.db, self.actor("test.create"), "test.create", {"test_code": "SCOPE", "test_name": "Scope"})
        actor = self.actor("test.view", "SELF"); actor.user_roles.append(assignment("user.view", "ORGANIZATION"))
        self.assertEqual(self.test_api.list(self.db, actor, "test.view"), [])
        actor.user_roles.append(assignment("test.view", "BUSINESS_UNIT"))
        self.assertEqual(len(self.test_api.list(self.db, actor, "test.view")), 1)

    def test_method_header_version_parameter_lifecycle_nested_concealment_and_audit(self):
        method = self.method_api.create(self.db, self.actor("method.create"), "method.create", {"method_code": "HPLC", "method_name": "HPLC"})
        version = self.methods.create_version(self.db, self.actor("method.create"), method.id, "method.create", {"version_number": 1})
        parameter = self.methods.create_parameter(self.db, self.actor("method.create"), method.id, version.id, "method.create", {"parameter_code": "FLOW", "parameter_name": "Flow", "value_type": "NUMBER"})
        parameter = self.methods.update_parameter(self.db, self.actor("method.update"), method.id, version.id, parameter.id, parameter.version, "method.update", {"unit": "mL/min"})
        with self.assertRaises(ResourceNotFoundException): self.methods.version(self.db, self.actor("method.view"), uuid4(), version.id, "method.view")
        version = self.methods.lifecycle(self.db, self.actor("method.update"), method.id, version.id, version.version, "method.update", "APPROVED")
        version = self.methods.lifecycle(self.db, self.actor("method.update"), method.id, version.id, version.version, "method.update", "SUPERSEDED")
        actions = [row.action for row in self.db.query(AuditEvent).filter(AuditEvent.entity_id.in_([version.id, parameter.id]))]
        self.assertIn("APPROVE", actions); self.assertIn("SUPERSEDE", actions); self.assertIn("UPDATE", actions)
        with self.assertRaises(ValidationException): self.methods.update_parameter(self.db, self.actor("method.update"), method.id, version.id, parameter.id, parameter.version, "method.update", {"unit": "x"})

    def test_lifecycle_expected_version_conflict(self):
        method = self.method_api.create(self.db, self.actor("method.create"), "method.create", {"method_code": "MVCC", "method_name": "MVCC"})
        version = self.methods.create_version(self.db, self.actor("method.create"), method.id, "method.create", {"version_number": 1})
        with self.assertRaises(VersionConflictException): self.methods.lifecycle(self.db, self.actor("method.update"), method.id, version.id, version.version + 1, "method.update", "APPROVED")

    def test_invalid_method_lifecycle_is_conflict(self):
        method = self.method_api.create(self.db, self.actor("method.create"), "method.create", {"method_code": "M2", "method_name": "M2"})
        version = self.methods.create_version(self.db, self.actor("method.create"), method.id, "method.create", {"version_number": 1})
        version = self.methods.lifecycle(self.db, self.actor("method.update"), method.id, version.id, version.version, "method.update", "RETIRED")
        with self.assertRaises(SecurityConflictException): self.methods.lifecycle(self.db, self.actor("method.update"), method.id, version.id, version.version, "method.update", "APPROVED")

    def test_specification_tree_readiness_exact_method_and_immutability(self):
        test = self.test_api.create(self.db, self.actor("test.create"), "test.create", {"test_code": "PURITY", "test_name": "Purity"})
        method = self.method_api.create(self.db, self.actor("method.create"), "method.create", {"method_code": "M3", "method_name": "M3"})
        method_version = self.methods.create_version(self.db, self.actor("method.create"), method.id, "method.create", {"version_number": 1})
        method_version = self.methods.lifecycle(self.db, self.actor("method.update"), method.id, method_version.id, method_version.version, "method.update", "APPROVED")
        specification = self.spec_api.create(self.db, self.actor("specification.create"), "specification.create", {"material_id": self.material.id, "specification_code": "FIN", "specification_name": "Finished"})
        version = self.specs.create_version(self.db, self.actor("specification.create"), specification.id, "specification.create", {"version_number": 1})
        item = self.specs.create_test(self.db, self.actor("specification.create"), specification.id, version.id, "specification.create", {"test_id": test.id, "method_version_id": method_version.id, "sequence_number": 1})
        self.assertEqual(item.method_version_id, method_version.id)
        limit = self.specs.create_limit(self.db, self.actor("specification.create"), specification.id, version.id, item.id, "specification.create", {"criterion_type": "BETWEEN", "lower_limit": 90, "upper_limit": 110})
        version = self.specs.lifecycle(self.db, self.actor("specification.update"), specification.id, version.id, version.version, "specification.update", "APPROVED")
        version = self.specs.lifecycle(self.db, self.actor("specification.update"), specification.id, version.id, version.version, "specification.update", "RETIRED")
        actions = [row.action for row in self.db.query(AuditEvent).filter(AuditEvent.entity_id == version.id)]
        self.assertIn("APPROVE", actions); self.assertIn("RETIRE", actions)
        with self.assertRaises(ValidationException): self.specs.update_limit(self.db, self.actor("specification.update"), specification.id, version.id, item.id, limit.id, limit.version, "specification.update", {"lower_limit": 95})

    def test_incomplete_specification_cannot_be_approved(self):
        specification = self.spec_api.create(self.db, self.actor("specification.create"), "specification.create", {"material_id": self.material.id, "specification_code": "EMPTY", "specification_name": "Empty"})
        version = self.specs.create_version(self.db, self.actor("specification.create"), specification.id, "specification.create", {"version_number": 1})
        with self.assertRaises(ValidationException): self.specs.lifecycle(self.db, self.actor("specification.update"), specification.id, version.id, version.version, "specification.update", "APPROVED")

    def test_audit_failure_rolls_back_header_create(self):
        service = HeaderService(TestService(), TestRepository(), "test_code"); service.audit_service = Mock()
        service.audit_service.record_create.side_effect = RuntimeError("audit failed")
        with self.assertRaises(RuntimeError): service.create(self.db, self.actor("test.create"), "test.create", {"test_code": "ROLLBACK", "test_name": "Rollback"})
        self.assertIsNone(self.db.query(Test).filter(Test.test_code == "ROLLBACK").first())

    def test_audit_vocabulary_is_bounded(self):
        self.assertEqual({AuditAction.APPROVE, AuditAction.RETIRE, AuditAction.SUPERSEDE}, {"APPROVE", "RETIRE", "SUPERSEDE"})


if __name__ == "__main__": unittest.main()
