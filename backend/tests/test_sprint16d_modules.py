import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.exceptions import CapabilityConflictException, VersionConflictException
from app.database.session import engine
from app.models.audit_event import AuditEvent
from app.models.module import Module, OrganizationModule
from app.models.organization.organization import Organization
from app.seeds.permissions import PERMISSION_CATALOG
from app.services.module_service import MODULE_CATALOG, MODULE_DEPENDENCIES, ModuleService
from app.main import app
from app.auth.dependencies import get_current_user
from app.dependencies.database import get_db


def permission_actor(code: str):
    permission = SimpleNamespace(permission_code=code, is_active=True)
    mapping = SimpleNamespace(is_active=True, permission=permission)
    role = SimpleNamespace(is_active=True, role_permissions=[mapping])
    assignment = SimpleNamespace(is_active=True, role=role, access_scope="ORGANIZATION")
    return SimpleNamespace(id=uuid4(), organization_id=uuid4(), user_roles=[assignment], force_password_change=False)


class ModuleCatalogTests(unittest.TestCase):
    def test_registry_and_permissions_are_unique_and_complete(self):
        codes = [item["code"] for item in MODULE_CATALOG]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertEqual(set(codes), {"PLATFORM", "CORE_LAB", "INSTRUMENTS", "STABILITY", "CALIBRATION", "MAINTENANCE", "QUALIFICATION", "INVENTORY", "CONTRACT_TESTING"})
        permissions = [item["permission_code"] for item in PERMISSION_CATALOG]
        self.assertEqual(permissions.count("module.view"), 1); self.assertEqual(permissions.count("module.manage"), 1)
        self.assertNotIn("INVENTORY", MODULE_DEPENDENCIES)


class ModuleApiSecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app); app.dependency_overrides[get_db] = lambda: Mock()

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_authentication_and_view_permission_are_independent(self):
        self.assertEqual(self.client.get("/modules/organization").status_code, 401)
        app.dependency_overrides[get_current_user] = lambda: permission_actor("user.view")
        self.assertEqual(self.client.get("/modules/organization").status_code, 403)

    def test_manage_permission_is_required_for_mutation(self):
        app.dependency_overrides[get_current_user] = lambda: permission_actor("module.view")
        self.assertEqual(self.client.put("/modules/INSTRUMENTS/enable", json={"version": 0}).status_code, 403)


class ModuleDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect(); self.transaction = self.connection.begin(); self.db = Session(bind=self.connection)
        self.organization = Organization(organization_code=f"M{uuid4().hex[:12]}", organization_name="Module Test")
        self.other = Organization(organization_code=f"N{uuid4().hex[:12]}", organization_name="Other")
        self.db.add_all([self.organization, self.other]); self.db.flush()
        self.actor = SimpleNamespace(id=None, organization_id=self.organization.id, business_unit_id=None, division_id=None, department_id=None)
        self.service = ModuleService()

    def tearDown(self):
        self.db.close()
        if self.transaction.is_active: self.transaction.rollback()
        self.connection.close()

    def test_core_is_implicit_and_non_disableable(self):
        self.assertTrue(self.service.is_enabled(self.db, self.organization.id, "PLATFORM"))
        self.assertTrue(self.service.is_enabled(self.db, self.organization.id, "CORE_LAB"))
        with self.assertRaises(CapabilityConflictException): self.service.disable(self.db, self.actor, "PLATFORM", 0)

    def test_dependencies_enable_disable_versions_and_audit(self):
        instruments = self.service.enable(self.db, self.actor, "INSTRUMENTS", 0)
        stability = self.service.enable(self.db, self.actor, "STABILITY", 0)
        stale_version = stability.version
        self.assertTrue(self.service.is_enabled(self.db, self.organization.id, "STABILITY"))
        with self.assertRaises(CapabilityConflictException): self.service.disable(self.db, self.actor, "INSTRUMENTS", instruments.version)
        self.service.disable(self.db, self.actor, "STABILITY", stability.version)
        actions = {row.action for row in self.db.query(AuditEvent).filter(AuditEvent.organization_id == self.organization.id).all()}
        self.assertTrue({"ACTIVATE", "DEACTIVATE"}.issubset(actions))
        with self.assertRaises(VersionConflictException): self.service.enable(self.db, self.actor, "STABILITY", stale_version)

    def test_unmet_dependency_and_organization_isolation(self):
        with self.assertRaisesRegex(CapabilityConflictException, "INSTRUMENTS"):
            self.service.enable(self.db, self.actor, "CALIBRATION", 0)
        self.service.enable(self.db, self.actor, "INSTRUMENTS", 0)
        self.assertFalse(self.service.is_enabled(self.db, self.other.id, "INSTRUMENTS"))

    def test_guard_allows_enabled_and_blocks_disabled(self):
        self.service.enable(self.db, self.actor, "INSTRUMENTS", 0)
        self.assertIs(self.service.require_enabled(self.db, self.actor, "INSTRUMENTS"), self.actor)
        with self.assertRaises(HTTPException) as caught: self.service.require_enabled(self.db, SimpleNamespace(organization_id=self.other.id), "INSTRUMENTS")
        self.assertEqual(caught.exception.status_code, 403)

    def test_audit_failure_rolls_back_mutation(self):
        service = ModuleService(); service.audit_service = Mock(); service.audit_service.record_update.side_effect = RuntimeError("audit failed")
        with self.assertRaises(RuntimeError): service.enable(self.db, self.actor, "INSTRUMENTS", 0)
        self.assertFalse(service.is_enabled(self.db, self.organization.id, "INSTRUMENTS"))


if __name__ == "__main__": unittest.main()
