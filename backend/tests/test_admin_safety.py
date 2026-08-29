import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.core.exceptions import SecurityConflictException
from app.dependencies.database import get_db
from app.main import app
from app.routers.user import security as user_security_router
from app.services.user.admin_safety_service import AdminSafetyService
from app.services.user.security_audit_service import SecurityAuditService
from app.services.user.security_service import SecurityService
from app.services.user_role_service import UserRoleService
from app.services.role_service import RoleService
from app.schemas.role import RoleStatusUpdate


class AdminSafetyServiceTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.admin_role = SimpleNamespace(id=uuid4(), is_active=True, role_code="ADMIN")
        self.target_id = uuid4()
        self.actor_id = uuid4()
        self.service = AdminSafetyService()
        self.service.repository = Mock()
        self.service.repository.lock_admin_role.return_value = self.admin_role
        self.service.audit_service = Mock()

    def test_cannot_deactivate_sole_usable_admin(self):
        self.service.repository.get_usable_admin_ids.return_value = {self.target_id}

        with self.assertRaises(SecurityConflictException):
            self.service.ensure_user_can_lose_admin_access(
                self.db,
                self.target_id,
                actor_user_id=self.actor_id,
                operation="DEACTIVATE_USER",
            )

        self.service.audit_service.record_event.assert_called_once_with(
            self.db,
            event_type=SecurityAuditService.ADMIN_SAFETY_BLOCKED,
            actor_user_id=self.actor_id,
            target_user_id=self.target_id,
            details={"operation": "DEACTIVATE_USER"},
        )
        self.db.commit.assert_called_once_with()

    def test_can_deactivate_admin_when_another_usable_admin_exists(self):
        self.service.repository.get_usable_admin_ids.return_value = {
            self.target_id,
            uuid4(),
        }

        self.service.ensure_user_can_lose_admin_access(
            self.db,
            self.target_id,
            actor_user_id=self.actor_id,
            operation="DEACTIVATE_USER",
        )

        self.service.audit_service.record_event.assert_not_called()

    def test_cannot_remove_admin_role_from_sole_usable_admin(self):
        self.service.repository.get_usable_admin_ids.return_value = {self.target_id}

        with self.assertRaises(SecurityConflictException):
            self.service.ensure_admin_assignment_can_be_removed(
                self.db,
                self.target_id,
                self.admin_role.id,
                actor_user_id=self.actor_id,
            )

    def test_can_remove_admin_role_when_backup_is_usable(self):
        self.service.repository.get_usable_admin_ids.return_value = {
            self.target_id,
            uuid4(),
        }

        self.service.ensure_admin_assignment_can_be_removed(
            self.db,
            self.target_id,
            self.admin_role.id,
            actor_user_id=self.actor_id,
        )

        self.service.audit_service.record_event.assert_not_called()

    def test_inactive_admin_does_not_count_as_backup(self):
        # Repository filtering excludes inactive users, leaving only the target.
        self.service.repository.get_usable_admin_ids.return_value = {self.target_id}

        with self.assertRaises(SecurityConflictException):
            self.service.ensure_user_can_lose_admin_access(
                self.db,
                self.target_id,
                actor_user_id=self.actor_id,
                operation="DEACTIVATE_USER",
            )

    def test_inactive_admin_role_provides_no_usable_backup(self):
        self.admin_role.is_active = False

        self.service.ensure_user_can_lose_admin_access(
            self.db,
            self.target_id,
            actor_user_id=self.actor_id,
            operation="DEACTIVATE_USER",
        )

        self.service.repository.get_usable_admin_ids.assert_not_called()

    def test_force_password_change_admin_still_counts_as_usable(self):
        # force_password_change is intentionally not part of repository filtering.
        forced_admin_id = uuid4()
        self.service.repository.get_usable_admin_ids.return_value = {
            self.target_id,
            forced_admin_id,
        }

        self.service.ensure_user_can_lose_admin_access(
            self.db,
            self.target_id,
            actor_user_id=self.actor_id,
            operation="DEACTIVATE_USER",
        )

        self.service.audit_service.record_event.assert_not_called()

    def test_non_admin_role_removal_is_unaffected(self):
        self.service.ensure_admin_assignment_can_be_removed(
            self.db,
            self.target_id,
            uuid4(),
            actor_user_id=self.actor_id,
        )

        self.service.repository.get_usable_admin_ids.assert_not_called()

    def test_admin_role_cannot_be_deactivated_while_usable_admin_exists(self):
        self.service.repository.get_usable_admin_ids.return_value = {self.target_id}

        with self.assertRaises(SecurityConflictException):
            self.service.ensure_role_can_be_deactivated(
                self.db,
                self.admin_role.id,
                actor_user_id=self.actor_id,
            )

    def test_blocked_deactivation_leaves_user_unchanged(self):
        user = SimpleNamespace(
            id=self.target_id,
            is_active=True,
            account_status="ACTIVE",
        )
        security_service = SecurityService()
        security_service.admin_safety_service = Mock()
        security_service.admin_safety_service.ensure_user_can_lose_admin_access.side_effect = (
            SecurityConflictException(AdminSafetyService.BLOCK_MESSAGE)
        )

        with self.assertRaises(SecurityConflictException):
            security_service.deactivate(
                self.db, user, actor_user_id=self.actor_id
            )

        self.assertTrue(user.is_active)
        self.assertEqual(user.account_status, "ACTIVE")

    def test_blocked_admin_assignment_removal_is_not_deleted(self):
        assignment = SimpleNamespace(id=uuid4())
        service = UserRoleService()
        service.repository = Mock()
        service.repository.get_assignment.return_value = assignment
        service.user_repository = Mock()
        service.user_repository.get.return_value = SimpleNamespace(id=self.target_id)
        service.scope_service = Mock()
        service.admin_safety_service = Mock()
        service.admin_safety_service.ensure_admin_assignment_can_be_removed.side_effect = (
            SecurityConflictException(AdminSafetyService.BLOCK_MESSAGE)
        )

        with self.assertRaises(SecurityConflictException):
            service.remove_role(
                self.db,
                self.target_id,
                self.admin_role.id,
                SimpleNamespace(id=self.actor_id),
            )

        service.repository.delete_assignment.assert_not_called()

    def test_blocked_admin_role_deactivation_leaves_role_active(self):
        service = RoleService()
        service.repository = Mock()
        service.repository.get.return_value = self.admin_role
        service.admin_safety_service = Mock()
        service.admin_safety_service.ensure_role_can_be_deactivated.side_effect = (
            SecurityConflictException(AdminSafetyService.BLOCK_MESSAGE)
        )

        with self.assertRaises(SecurityConflictException):
            service.update_status(
                self.db,
                self.admin_role.id,
                RoleStatusUpdate(is_active=False),
                actor_user_id=self.actor_id,
            )

        self.assertTrue(self.admin_role.is_active)
        service.repository.update.assert_not_called()

    def test_block_event_has_only_safe_metadata(self):
        self.service.repository.get_usable_admin_ids.return_value = {self.target_id}

        with self.assertRaises(SecurityConflictException):
            self.service.ensure_user_can_lose_admin_access(
                self.db,
                self.target_id,
                actor_user_id=self.actor_id,
                operation="DELETE_USER",
            )

        kwargs = self.service.audit_service.record_event.call_args.kwargs
        self.assertEqual(kwargs["details"], {"operation": "DELETE_USER"})
        self.assertNotIn("password", repr(kwargs).lower())
        self.assertNotIn("authorization", repr(kwargs).lower())


class AdminSafetyApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        permission = SimpleNamespace(permission_code="user.update", is_active=True)
        role_permission = SimpleNamespace(is_active=True, permission=permission)
        role = SimpleNamespace(is_active=True, role_permissions=[role_permission])
        self.actor = SimpleNamespace(
            id=uuid4(),
            organization_id=uuid4(),
            business_unit_id=uuid4(),
            division_id=uuid4(),
            department_id=uuid4(),
            force_password_change=False,
            user_roles=[SimpleNamespace(is_active=True, role=role, access_scope="ORGANIZATION")],
        )
        app.dependency_overrides[get_db] = lambda: Mock()
        app.dependency_overrides[get_current_user] = lambda: self.actor

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_rejected_deactivation_returns_409(self):
        target_id = uuid4()
        with (
            patch.object(
                user_security_router.service,
                "get_user",
                return_value=SimpleNamespace(id=target_id, organization_id=self.actor.organization_id),
            ),
            patch.object(
                user_security_router.service,
                "deactivate",
                side_effect=SecurityConflictException(AdminSafetyService.BLOCK_MESSAGE),
            ),
        ):
            response = self.client.put(
                f"/users/{target_id}/deactivate",
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], AdminSafetyService.BLOCK_MESSAGE)


if __name__ == "__main__":
    unittest.main()
