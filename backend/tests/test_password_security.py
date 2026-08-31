import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.auth_service import AuthService
from app.auth.hashing import hash_password, verify_password
from app.auth.password_policy import PasswordPolicy
from app.core.exceptions import ValidationException
from app.dependencies.database import get_db
from app.main import app
from app.models.user.user import User
from app.routers.auth import auth as auth_router
from app.routers.user import security as user_security_router
from app.services.user.password_service import PasswordService
from app.services.user.security_audit_service import SecurityAuditService
from app.services.user.user_service import UserService
from app.schemas.user.user import UserCreate


COMPLIANT_PASSWORD = "StrongPass!42"
NEW_COMPLIANT_PASSWORD = "NewStrongPass!43"


class PasswordPolicyTests(unittest.TestCase):
    def test_accepts_compliant_password(self):
        PasswordPolicy.validate(COMPLIANT_PASSWORD)

    def assert_policy_rejects(self, password: str, expected_message: str):
        with self.assertRaises(ValidationException) as error:
            PasswordPolicy.validate(password)
        self.assertIn(expected_message, str(error.exception))
        self.assertNotIn(password, str(error.exception))

    def test_rejects_too_short(self):
        self.assert_policy_rejects("Aa1!short", "at least 12")

    def test_rejects_missing_uppercase(self):
        self.assert_policy_rejects("lowercase!123", "uppercase")

    def test_rejects_missing_lowercase(self):
        self.assert_policy_rejects("UPPERCASE!123", "lowercase")

    def test_rejects_missing_digit(self):
        self.assert_policy_rejects("NoDigitsHere!", "digit")

    def test_rejects_missing_special_character(self):
        self.assert_policy_rejects("NoSpecial1234", "special")


class PasswordServiceTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.user = SimpleNamespace(
            id=uuid4(),
            username="password-test-user",
            password_hash=hash_password(COMPLIANT_PASSWORD),
            password_changed_at=None,
            force_password_change=True,
            failed_login_attempts=4,
            locked_until=datetime(2026, 9, 1),
            account_status="LOCKED",
            is_active=True,
        )
        self.service = PasswordService()
        self.service.repository = Mock()
        self.service.repository.save.side_effect = lambda _db, user: user
        self.service.audit_service = Mock()

    def test_change_password_updates_security_state_and_event(self):
        old_changed_at = self.user.password_changed_at

        result = self.service.change_password(
            self.db,
            self.user,
            current_password=COMPLIANT_PASSWORD,
            new_password=NEW_COMPLIANT_PASSWORD,
            confirm_new_password=NEW_COMPLIANT_PASSWORD,
        )

        self.assertIs(result, self.user)
        self.assertFalse(verify_password(COMPLIANT_PASSWORD, result.password_hash))
        self.assertTrue(verify_password(NEW_COMPLIANT_PASSWORD, result.password_hash))
        self.assertNotEqual(result.password_changed_at, old_changed_at)
        self.assertFalse(result.force_password_change)
        self.assertEqual(result.failed_login_attempts, 0)
        self.assertIsNone(result.locked_until)
        self.service.audit_service.record_event.assert_called_once_with(
            self.db,
            event_type=SecurityAuditService.PASSWORD_CHANGED,
            actor_user_id=self.user.id,
            target_user_id=self.user.id,
        )
        self.db.commit.assert_called_once_with()

    def test_first_password_change_preserves_pending_until_admin_activation(self):
        self.user.account_status = "PENDING"
        result = self.service.change_password(
            self.db,
            self.user,
            current_password=COMPLIANT_PASSWORD,
            new_password=NEW_COMPLIANT_PASSWORD,
            confirm_new_password=NEW_COMPLIANT_PASSWORD,
        )
        self.assertFalse(result.force_password_change)
        self.assertTrue(result.is_active)
        self.assertEqual(result.account_status, "PENDING")

    def test_wrong_current_password_is_rejected(self):
        with self.assertRaises(ValidationException) as error:
            self.service.change_password(
                self.db,
                self.user,
                current_password="WrongCurrent!99",
                new_password=NEW_COMPLIANT_PASSWORD,
                confirm_new_password=NEW_COMPLIANT_PASSWORD,
            )
        self.assertEqual(str(error.exception), "Current password is incorrect.")
        self.assertNotIn("WrongCurrent!99", str(error.exception))
        self.db.commit.assert_not_called()

    def test_mismatched_confirmation_is_rejected(self):
        with self.assertRaises(ValidationException):
            self.service.change_password(
                self.db,
                self.user,
                current_password=COMPLIANT_PASSWORD,
                new_password=NEW_COMPLIANT_PASSWORD,
                confirm_new_password="DifferentPass!44",
            )
        self.db.commit.assert_not_called()

    def test_same_current_and_new_password_is_rejected(self):
        with self.assertRaises(ValidationException) as error:
            self.service.change_password(
                self.db,
                self.user,
                current_password=COMPLIANT_PASSWORD,
                new_password=COMPLIANT_PASSWORD,
                confirm_new_password=COMPLIANT_PASSWORD,
            )
        self.assertIn("different", str(error.exception))
        self.db.commit.assert_not_called()

    def test_admin_reset_sets_force_change_and_clears_lock(self):
        actor_id = uuid4()

        result = self.service.reset_password(
            self.db,
            self.user,
            actor_user_id=actor_id,
            new_password=NEW_COMPLIANT_PASSWORD,
            confirm_new_password=NEW_COMPLIANT_PASSWORD,
        )

        self.assertTrue(verify_password(NEW_COMPLIANT_PASSWORD, result.password_hash))
        self.assertTrue(result.force_password_change)
        self.assertIsNotNone(result.password_changed_at)
        self.assertEqual(result.failed_login_attempts, 0)
        self.assertIsNone(result.locked_until)
        self.assertEqual(result.account_status, "ACTIVE")
        self.service.audit_service.record_event.assert_called_once_with(
            self.db,
            event_type=SecurityAuditService.PASSWORD_RESET,
            actor_user_id=actor_id,
            target_user_id=self.user.id,
        )

    def test_admin_reset_does_not_reactivate_inactive_user(self):
        self.user.is_active = False
        self.user.account_status = "INACTIVE"

        result = self.service.reset_password(
            self.db,
            self.user,
            actor_user_id=uuid4(),
            new_password=NEW_COMPLIANT_PASSWORD,
            confirm_new_password=NEW_COMPLIANT_PASSWORD,
        )

        self.assertFalse(result.is_active)
        self.assertEqual(result.account_status, "INACTIVE")

    def test_admin_reset_preserves_non_lock_account_status(self):
        self.user.account_status = "PENDING"

        result = self.service.reset_password(
            self.db,
            self.user,
            actor_user_id=uuid4(),
            new_password=NEW_COMPLIANT_PASSWORD,
            confirm_new_password=NEW_COMPLIANT_PASSWORD,
        )

        self.assertEqual(result.account_status, "PENDING")

    def test_password_events_contain_no_credentials(self):
        self.service.reset_password(
            self.db,
            self.user,
            actor_user_id=uuid4(),
            new_password=NEW_COMPLIANT_PASSWORD,
            confirm_new_password=NEW_COMPLIANT_PASSWORD,
        )
        kwargs = self.service.audit_service.record_event.call_args.kwargs
        self.assertNotIn("details", kwargs)
        serialized = repr(kwargs)
        self.assertNotIn(NEW_COMPLIANT_PASSWORD, serialized)
        self.assertNotIn(self.user.password_hash, serialized)

    def test_old_password_login_fails_and_new_password_login_succeeds(self):
        self.service.change_password(
            self.db,
            self.user,
            current_password=COMPLIANT_PASSWORD,
            new_password=NEW_COMPLIANT_PASSWORD,
            confirm_new_password=NEW_COMPLIANT_PASSWORD,
        )
        auth_service = AuthService()
        auth_service.user_repository = Mock()
        auth_service.user_repository.get_by_username.return_value = self.user
        auth_service.security_service = Mock()
        auth_service.security_service.is_locked.return_value = False
        auth_service.security_service.audit_service = Mock()

        with self.assertRaises(HTTPException):
            auth_service.authenticate_user(
                Mock(), self.user.username, COMPLIANT_PASSWORD
            )

        authenticated = auth_service.authenticate_user(
            Mock(), self.user.username, NEW_COMPLIANT_PASSWORD
        )
        self.assertIs(authenticated, self.user)


class UserCreationPasswordTests(unittest.TestCase):
    def setUp(self):
        self.service = UserService()
        self.service.repository = Mock()
        self.service.repository.create.side_effect = lambda _db, user: user
        self.service.repository.get_by_username.return_value = None
        self.service.repository.get_by_email.return_value = None
        self.service.repository.get_by_employee_code.return_value = None
        self.service.scope_service = Mock()

    @staticmethod
    def make_user(password: str) -> UserCreate:
        return UserCreate(
            organization_id=uuid4(),
            business_unit_id=uuid4(),
            division_id=uuid4(),
            department_id=uuid4(),
            designation_id=uuid4(),
            employee_code="EMP-PASSWORD-TEST",
            first_name="Password",
            last_name="Test",
            display_name="Password Test",
            email="password-test@example.com",
            username="password-create-test",
            password=password,
        )

    def test_user_creation_rejects_noncompliant_password(self):
        with self.assertRaises(ValidationException):
            self.service.create(Mock(), self.make_user("weak"), Mock())
        self.service.repository.create.assert_not_called()

    def test_user_creation_initializes_password_lifecycle(self):
        created = self.service.create(Mock(), self.make_user(COMPLIANT_PASSWORD), Mock())

        self.assertTrue(verify_password(COMPLIANT_PASSWORD, created.password_hash))
        self.assertIsNotNone(created.password_changed_at)
        self.assertTrue(created.force_password_change)

    def test_user_model_account_lifecycle_starts_pending(self):
        self.assertEqual(User.__table__.c.account_status.default.arg, "PENDING")


class PasswordApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.user = SimpleNamespace(
            id=uuid4(),
            organization_id=uuid4(),
            business_unit_id=uuid4(),
            division_id=uuid4(),
            department_id=uuid4(),
            username="forced-user",
            email="forced@example.com",
            display_name="Forced User",
            force_password_change=True,
            user_roles=[],
        )
        app.dependency_overrides[get_db] = lambda: Mock()
        app.dependency_overrides[get_current_user] = lambda: self.user

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_forced_user_can_access_me(self):
        response = self.client.get(
            "/auth/me", headers={"Authorization": "Bearer test-token"}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["force_password_change"])
        self.assertEqual(body["permissions"], [])
        self.assertTrue({"password", "password_hash", "token", "locked_until"}.isdisjoint(body))

    def test_me_returns_false_force_password_change_and_effective_permissions(self):
        active_permission = SimpleNamespace(
            permission_code="user.view", is_active=True,
        )
        inactive_permission = SimpleNamespace(
            permission_code="user.update", is_active=False,
        )
        role = SimpleNamespace(
            is_active=True,
            role_permissions=[
                SimpleNamespace(is_active=True, permission=active_permission),
                SimpleNamespace(is_active=True, permission=inactive_permission),
            ],
        )
        self.user.force_password_change = False
        self.user.user_roles = [SimpleNamespace(is_active=True, role=role)]

        response = self.client.get(
            "/auth/me", headers={"Authorization": "Bearer test-token"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["force_password_change"])
        self.assertEqual(response.json()["permissions"], ["user.view"])

    def test_forced_user_can_access_change_password(self):
        with patch.object(auth_router.password_service, "change_password") as change:
            response = self.client.post(
                "/auth/change-password",
                headers={"Authorization": "Bearer test-token"},
                json={
                    "current_password": COMPLIANT_PASSWORD,
                    "new_password": NEW_COMPLIANT_PASSWORD,
                    "confirm_new_password": NEW_COMPLIANT_PASSWORD,
                },
            )
        self.assertEqual(response.status_code, 200)
        change.assert_called_once()

    def test_forced_user_is_blocked_from_permission_endpoint(self):
        response = self.client.get(
            "/users/", headers={"Authorization": "Bearer test-token"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "Password change is required before accessing this resource.",
        )

    def test_unauthorized_admin_reset_returns_403(self):
        self.user.force_password_change = False
        response = self.client.post(
            f"/users/{uuid4()}/reset-password",
            headers={"Authorization": "Bearer test-token"},
            json={
                "new_password": NEW_COMPLIANT_PASSWORD,
                "confirm_new_password": NEW_COMPLIANT_PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_reset_succeeds_with_user_update(self):
        permission = SimpleNamespace(
            permission_code="user.update",
            is_active=True,
        )
        role_permission = SimpleNamespace(is_active=True, permission=permission)
        role = SimpleNamespace(
            is_active=True,
            role_permissions=[role_permission],
        )
        self.user.force_password_change = False
        self.user.user_roles = [SimpleNamespace(is_active=True, role=role, access_scope="ORGANIZATION")]
        target_id = uuid4()
        target = SimpleNamespace(id=target_id, organization_id=self.user.organization_id)

        with (
            patch.object(
                user_security_router.service, "get_user", return_value=target
            ),
            patch.object(user_security_router.password_service, "reset_password") as reset,
        ):
            response = self.client.post(
                f"/users/{target_id}/reset-password",
                headers={"Authorization": "Bearer test-token"},
                json={
                    "new_password": NEW_COMPLIANT_PASSWORD,
                    "confirm_new_password": NEW_COMPLIANT_PASSWORD,
                },
            )

        self.assertEqual(response.status_code, 200)
        reset.assert_called_once()


if __name__ == "__main__":
    unittest.main()
