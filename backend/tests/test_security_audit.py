import unittest
from types import SimpleNamespace
from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth.auth_service import AuthService
from app.auth.dependencies import get_current_user
from app.dependencies.database import get_db
from app.main import app
from app.routers import security_history
from app.services.user.security_audit_service import SecurityAuditService
from app.services.user.security_service import SecurityService


class SecurityServiceAuditTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.user = SimpleNamespace(
            id=uuid4(),
            is_active=True,
            account_status="ACTIVE",
            failed_login_attempts=0,
            locked_until=None,
        )
        self.service = SecurityService()
        self.service.repository = Mock()
        self.service.repository.save.side_effect = lambda db, user: user
        self.service.repository.record_login_failure.side_effect = (
            lambda db, user, attempts, locked_until: self._apply_failure(
                user, attempts, locked_until
            )
        )
        self.service.audit_service = Mock()
        self.service.admin_safety_service = Mock()

    @staticmethod
    def _apply_failure(user, attempts, locked_until):
        user.failed_login_attempts = attempts
        user.locked_until = locked_until
        return user

    @patch("app.services.user.security_service.settings.MAX_FAILED_LOGIN_ATTEMPTS", 2)
    def test_failed_login_reaching_threshold_locks_account(self):
        self.user.failed_login_attempts = 1

        self.service.record_failed_login(self.db, self.user)

        self.assertEqual(self.user.account_status, "LOCKED")
        self.assertEqual(self.user.failed_login_attempts, 2)
        self.assertIsNotNone(self.user.locked_until)

    def test_unlock_records_actor_and_target_in_same_commit(self):
        actor_id = uuid4()
        self.user.account_status = "LOCKED"
        self.user.failed_login_attempts = 5

        result = self.service.unlock(self.db, self.user, actor_user_id=actor_id)

        self.assertIs(result, self.user)
        self.assertEqual(result.account_status, "ACTIVE")
        self.assertEqual(result.failed_login_attempts, 0)
        self.service.audit_service.record_event.assert_called_once_with(
            self.db,
            event_type=SecurityAuditService.ACCOUNT_UNLOCKED,
            actor_user_id=actor_id,
            target_user_id=self.user.id,
        )
        self.db.commit.assert_called_once_with()

    def test_unlock_does_not_reactivate_inactive_account(self):
        self.user.is_active = False
        self.user.account_status = "LOCKED"
        self.user.failed_login_attempts = 5

        result = self.service.unlock(self.db, self.user, actor_user_id=uuid4())

        self.assertFalse(result.is_active)
        self.assertEqual(result.account_status, "INACTIVE")
        self.assertEqual(result.failed_login_attempts, 0)
        self.assertIsNone(result.locked_until)

    def test_activate_and_deactivate_record_events(self):
        actor_id = uuid4()

        self.service.deactivate(self.db, self.user, actor_user_id=actor_id)
        self.assertFalse(self.user.is_active)
        self.service.audit_service.record_event.assert_called_with(
            self.db,
            event_type=SecurityAuditService.ACCOUNT_DEACTIVATED,
            actor_user_id=actor_id,
            target_user_id=self.user.id,
        )

        self.service.activate(self.db, self.user, actor_user_id=actor_id)
        self.assertTrue(self.user.is_active)
        self.service.audit_service.record_event.assert_called_with(
            self.db,
            event_type=SecurityAuditService.ACCOUNT_ACTIVATED,
            actor_user_id=actor_id,
            target_user_id=self.user.id,
        )


class AuthenticationAuditTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.user = SimpleNamespace(
            id=uuid4(),
            username="audit-test-user",
            password_hash="not-a-real-hash",
            is_active=True,
            account_status="ACTIVE",
            failed_login_attempts=0,
            locked_until=None,
        )
        self.service = AuthService()
        self.service.user_repository = Mock()
        self.service.user_repository.get_by_username.return_value = self.user
        self.service.security_service = Mock()
        self.service.security_service.is_locked.return_value = False
        self.service.security_service.audit_service = Mock()

    def tearDown(self):
        app.dependency_overrides.clear()

    @patch("app.auth.auth_service.verify_password", return_value=True)
    def test_success_records_history_and_event(self, _verify_password):
        self.user.failed_login_attempts = 3

        def reset_security_state(_db, user):
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login = datetime(2026, 8, 29)

        self.service.security_service.record_successful_login.side_effect = (
            reset_security_state
        )
        result = self.service.authenticate_user(
            self.db,
            self.user.username,
            "discarded-test-value",
            ip_address="127.0.0.1",
            user_agent="unit-test",
        )

        self.assertIs(result, self.user)
        self.assertEqual(result.failed_login_attempts, 0)
        self.assertIsNotNone(result.last_login)
        self.service.security_service.audit_service.record_login.assert_called_once_with(
            self.db,
            username=self.user.username,
            user_id=self.user.id,
            success=True,
            ip_address="127.0.0.1",
            user_agent="unit-test",
        )
        self.service.security_service.audit_service.record_event.assert_called_once_with(
            self.db,
            event_type=SecurityAuditService.LOGIN_SUCCESS,
            actor_user_id=self.user.id,
            target_user_id=self.user.id,
        )
        self.db.commit.assert_called_once_with()

    @patch("app.auth.auth_service.verify_password", return_value=False)
    def test_wrong_password_increments_failed_attempts_and_writes_history(
        self, _verify_password
    ):
        def increment(_db, user):
            user.failed_login_attempts += 1

        self.service.security_service.record_failed_login.side_effect = increment

        with self.assertRaises(HTTPException):
            self.service.authenticate_user(
                self.db, self.user.username, "discarded-test-value"
            )

        self.assertEqual(self.user.failed_login_attempts, 1)
        self.service.security_service.audit_service.record_login.assert_called_once_with(
            self.db,
            username=self.user.username,
            user_id=self.user.id,
            success=False,
            failure_reason="INVALID_CREDENTIALS",
            ip_address=None,
            user_agent=None,
        )

    @patch("app.auth.auth_service.verify_password")
    def test_locked_account_rejects_before_password_verification(self, verify):
        self.user.account_status = "LOCKED"
        self.service.security_service.is_locked.return_value = True

        with self.assertRaises(HTTPException) as error:
            self.service.authenticate_user(
                self.db, self.user.username, "discarded-test-value"
            )

        self.assertEqual(error.exception.detail, "Account is temporarily locked")
        verify.assert_not_called()

    @patch("app.auth.auth_service.verify_password")
    def test_inactive_account_rejects_before_password_verification(self, verify):
        self.user.is_active = False

        with self.assertRaises(HTTPException) as error:
            self.service.authenticate_user(
                self.db, self.user.username, "discarded-test-value"
            )

        self.assertEqual(error.exception.detail, "Account is inactive")
        verify.assert_not_called()

    @patch("app.auth.auth_service.verify_password", return_value=False)
    def test_failure_and_lockout_recorded_together(self, _verify_password):
        def lock_user(_db, user):
            user.failed_login_attempts = 5
            user.account_status = "LOCKED"

        self.service.security_service.record_failed_login.side_effect = lock_user

        with self.assertRaises(HTTPException) as error:
            self.service.authenticate_user(
                self.db, self.user.username, "discarded-test-value"
            )

        self.assertEqual(error.exception.status_code, 401)
        event_types = [
            call.kwargs["event_type"]
            for call in self.service.security_service.audit_service.record_event.call_args_list
        ]
        self.assertEqual(
            event_types,
            [SecurityAuditService.LOGIN_FAILURE, SecurityAuditService.ACCOUNT_LOCKED],
        )
        self.db.commit.assert_called_once_with()


class SecurityHistoryApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.original_service = security_history.service
        security_history.service = Mock()
        security_history.service.list_login_history.return_value = []
        security_history.service.list_security_events.return_value = []
        app.dependency_overrides[get_db] = lambda: Mock()

    def tearDown(self):
        security_history.service = self.original_service
        app.dependency_overrides.clear()

    def test_history_endpoint_requires_authentication(self):
        response = self.client.get("/security/login-history")
        self.assertEqual(response.status_code, 401)

    def test_history_endpoint_requires_user_view(self):
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            user_roles=[], force_password_change=False
        )
        response = self.client.get(
            "/security/login-history", headers={"Authorization": "Bearer test-token"}
        )
        self.assertEqual(response.status_code, 403)

    def test_history_pagination_is_forwarded(self):
        app.dependency_overrides[security_history.can_view_security_history] = (
            lambda: SimpleNamespace(id=uuid4())
        )
        response = self.client.get("/security/login-history?limit=25&offset=10")

        self.assertEqual(response.status_code, 200)
        security_history.service.list_login_history.assert_called_once_with(
            unittest.mock.ANY, limit=25, offset=10
        )

    def test_event_pagination_bounds_are_validated(self):
        app.dependency_overrides[security_history.can_view_security_history] = (
            lambda: SimpleNamespace(id=uuid4())
        )
        response = self.client.get("/security/events?limit=501")
        self.assertEqual(response.status_code, 422)


class CredentialExclusionTests(unittest.TestCase):
    def test_audit_models_have_no_credential_fields(self):
        prohibited = {
            "password",
            "password_hash",
            "jwt",
            "access_token",
            "authorization",
            "authorization_header",
            "client_secret",
        }
        audit_service = SecurityAuditService()
        audit_service.repository = Mock()
        audit_service.repository.add_login_history.side_effect = lambda _db, row: row
        audit_service.repository.add_security_event.side_effect = lambda _db, row: row

        history = audit_service.record_login(
            Mock(), username="user", success=False, failure_reason="INVALID_CREDENTIALS"
        )
        event = audit_service.record_event(
            Mock(),
            event_type=SecurityAuditService.LOGIN_FAILURE,
            details={
                "failure_reason": "INVALID_CREDENTIALS",
                "password": "must-not-survive",
                "nested": {"authorization": "must-not-survive", "safe": True},
            },
        )

        self.assertTrue(prohibited.isdisjoint(history.__dict__))
        self.assertTrue(prohibited.isdisjoint(event.__dict__))
        self.assertEqual(
            event.details,
            {"failure_reason": "INVALID_CREDENTIALS", "nested": {"safe": True}},
        )

if __name__ == "__main__":
    unittest.main()
