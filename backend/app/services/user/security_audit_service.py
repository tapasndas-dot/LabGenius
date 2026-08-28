from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user.login_history import LoginHistory
from app.models.user.security_event import SecurityEvent
from app.repositories.user.security_audit_repository import SecurityAuditRepository


class SecurityAuditService:
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    ACCOUNT_UNLOCKED = "ACCOUNT_UNLOCKED"
    ACCOUNT_ACTIVATED = "ACCOUNT_ACTIVATED"
    ACCOUNT_DEACTIVATED = "ACCOUNT_DEACTIVATED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET = "PASSWORD_RESET"
    ADMIN_SAFETY_BLOCKED = "ADMIN_SAFETY_BLOCKED"

    _PROHIBITED_DETAIL_KEYS = {
        "access_token",
        "authorization",
        "authorization_header",
        "client_secret",
        "jwt",
        "password",
        "password_hash",
        "refresh_token",
        "token",
    }

    def __init__(self) -> None:
        self.repository = SecurityAuditRepository()

    def record_login(
        self,
        db: Session,
        *,
        username: str,
        success: bool,
        user_id: UUID | None = None,
        failure_reason: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LoginHistory:
        return self.repository.add_login_history(
            db,
            LoginHistory(
                user_id=user_id,
                username_attempted=username[:255],
                success=success,
                failure_reason=failure_reason,
                ip_address=ip_address[:45] if ip_address else None,
                user_agent=user_agent[:512] if user_agent else None,
            ),
        )

    def record_event(
        self,
        db: Session,
        *,
        event_type: str,
        actor_user_id: UUID | None = None,
        target_user_id: UUID | None = None,
        details: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        return self.repository.add_security_event(
            db,
            SecurityEvent(
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                event_type=event_type,
                details=self._sanitize_details(details),
            ),
        )

    @classmethod
    def _sanitize_details(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: cls._sanitize_details(item)
                for key, item in value.items()
                if key.lower() not in cls._PROHIBITED_DETAIL_KEYS
            }
        if isinstance(value, list):
            return [cls._sanitize_details(item) for item in value]
        return value

    def list_login_history(self, db: Session, **kwargs) -> list[LoginHistory]:
        return self.repository.list_login_history(db, **kwargs)

    def list_security_events(self, db: Session, **kwargs) -> list[SecurityEvent]:
        return self.repository.list_security_events(db, **kwargs)
