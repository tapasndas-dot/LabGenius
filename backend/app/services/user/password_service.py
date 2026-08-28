from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.hashing import hash_password, verify_password
from app.auth.password_policy import PasswordPolicy
from app.core.exceptions import ValidationException
from app.models.user.user import User
from app.repositories.user.security_repository import SecurityRepository
from app.services.user.security_audit_service import SecurityAuditService


class PasswordService:
    def __init__(self) -> None:
        self.repository = SecurityRepository()
        self.audit_service = SecurityAuditService()

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _validate_confirmation(new_password: str, confirmation: str) -> None:
        if new_password != confirmation:
            raise ValidationException("New password and confirmation do not match.")

    def change_password(
        self,
        db: Session,
        user: User,
        *,
        current_password: str,
        new_password: str,
        confirm_new_password: str,
    ) -> User:
        self._validate_confirmation(new_password, confirm_new_password)

        if not verify_password(current_password, user.password_hash):
            raise ValidationException("Current password is incorrect.")
        if verify_password(new_password, user.password_hash):
            raise ValidationException("New password must be different from current password.")

        PasswordPolicy.validate(new_password)
        user.password_hash = hash_password(new_password)
        user.password_changed_at = self._utc_now()
        user.force_password_change = False
        user.failed_login_attempts = 0
        user.locked_until = None

        self.repository.save(db, user)
        self.audit_service.record_event(
            db,
            event_type=SecurityAuditService.PASSWORD_CHANGED,
            actor_user_id=user.id,
            target_user_id=user.id,
        )
        db.commit()
        db.refresh(user)
        return user

    def reset_password(
        self,
        db: Session,
        target_user: User,
        *,
        actor_user_id: UUID,
        new_password: str,
        confirm_new_password: str,
    ) -> User:
        self._validate_confirmation(new_password, confirm_new_password)
        PasswordPolicy.validate(new_password)

        target_user.password_hash = hash_password(new_password)
        target_user.password_changed_at = self._utc_now()
        target_user.force_password_change = True
        target_user.failed_login_attempts = 0
        target_user.locked_until = None
        if target_user.account_status == "LOCKED":
            target_user.account_status = (
                "ACTIVE" if target_user.is_active else "INACTIVE"
            )

        self.repository.save(db, target_user)
        self.audit_service.record_event(
            db,
            event_type=SecurityAuditService.PASSWORD_RESET,
            actor_user_id=actor_user_id,
            target_user_id=target_user.id,
        )
        db.commit()
        db.refresh(target_user)
        return target_user
