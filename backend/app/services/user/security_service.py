from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ResourceNotFoundException

from app.models.user.user import User

from app.repositories.user.security_repository import (
    SecurityRepository,
)
from app.services.user.security_audit_service import SecurityAuditService


class SecurityService:

    def __init__(self):
        self.repository = SecurityRepository()
        self.audit_service = SecurityAuditService()

    def get_user(
        self,
        db: Session,
        user_id: UUID,
    ) -> User:

        user = self.repository.get_user(
            db,
            user_id,
        )

        if user is None:
            raise ResourceNotFoundException(
                "User not found."
            )

        return user

    def activate(
        self,
        db: Session,
        user: User,
        actor_user_id: UUID | None = None,
    ) -> User:

        user.is_active = True

        if user.account_status != "LOCKED":
            user.account_status = "ACTIVE"

        self.repository.save(db, user)
        self.audit_service.record_event(
            db,
            event_type=SecurityAuditService.ACCOUNT_ACTIVATED,
            actor_user_id=actor_user_id,
            target_user_id=user.id,
        )
        db.commit()
        db.refresh(user)
        return user

    def deactivate(
        self,
        db: Session,
        user: User,
        actor_user_id: UUID | None = None,
    ) -> User:

        user.is_active = False
        user.account_status = "INACTIVE"

        self.repository.save(db, user)
        self.audit_service.record_event(
            db,
            event_type=SecurityAuditService.ACCOUNT_DEACTIVATED,
            actor_user_id=actor_user_id,
            target_user_id=user.id,
        )
        db.commit()
        db.refresh(user)
        return user

    def unlock(
        self,
        db: Session,
        user: User,
        actor_user_id: UUID | None = None,
    ) -> User:

        user.failed_login_attempts = 0
        user.locked_until = None
        user.account_status = "ACTIVE" if user.is_active else "INACTIVE"

        self.repository.save(db, user)
        self.audit_service.record_event(
            db,
            event_type=SecurityAuditService.ACCOUNT_UNLOCKED,
            actor_user_id=actor_user_id,
            target_user_id=user.id,
        )
        db.commit()
        db.refresh(user)
        return user

    def record_successful_login(
        self,
        db: Session,
        user: User,
    ) -> User:

        # User security columns are timestamp without time zone in the
        # existing schema, so store naive UTC consistently.
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        return self.repository.record_login_success(
            db,
            user,
            now,
        )

    def record_failed_login(
        self,
        db: Session,
        user: User,
    ) -> User:

        attempts = (
            user.failed_login_attempts + 1
        )

        locked_until = None

        if attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:

            locked_until = (
                datetime.now(timezone.utc).replace(tzinfo=None)
                + timedelta(
                    minutes=settings.ACCOUNT_LOCKOUT_MINUTES
                )
            )

            user.account_status = "LOCKED"

        return self.repository.record_login_failure(
            db,
            user,
            attempts,
            locked_until,
        )

    def is_locked(
        self,
        user: User,
    ) -> bool:

        if user.account_status != "LOCKED":
            return False

        if user.locked_until is None:
            return True

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        return user.locked_until > now
