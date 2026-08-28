from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import SecurityConflictException
from app.repositories.user.admin_safety_repository import AdminSafetyRepository
from app.services.user.security_audit_service import SecurityAuditService


class AdminSafetyService:
    ADMIN_ROLE_CODE = "ADMIN"
    BLOCK_MESSAGE = "Operation would remove the final usable administrator."

    def __init__(self) -> None:
        self.repository = AdminSafetyRepository()
        self.audit_service = SecurityAuditService()

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def ensure_user_can_lose_admin_access(
        self,
        db: Session,
        target_user_id: UUID,
        *,
        actor_user_id: UUID | None,
        operation: str,
    ) -> None:
        admin_role = self.repository.lock_admin_role(db)
        if admin_role is None or not admin_role.is_active:
            return

        usable_ids = self.repository.get_usable_admin_ids(
            db, admin_role.id, self._utc_now()
        )
        if target_user_id not in usable_ids or len(usable_ids) > 1:
            return

        self._block(
            db,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            operation=operation,
        )

    def ensure_admin_assignment_can_be_removed(
        self,
        db: Session,
        target_user_id: UUID,
        role_id: UUID,
        *,
        actor_user_id: UUID | None,
    ) -> None:
        admin_role = self.repository.lock_admin_role(db)
        if admin_role is None or admin_role.id != role_id or not admin_role.is_active:
            return

        usable_ids = self.repository.get_usable_admin_ids(
            db, admin_role.id, self._utc_now()
        )
        if target_user_id in usable_ids and len(usable_ids) == 1:
            self._block(
                db,
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                operation="REMOVE_ADMIN_ROLE",
            )

    def ensure_role_can_be_deactivated(
        self,
        db: Session,
        role_id: UUID,
        *,
        actor_user_id: UUID | None,
    ) -> None:
        admin_role = self.repository.lock_admin_role(db)
        if admin_role is None or admin_role.id != role_id or not admin_role.is_active:
            return

        usable_ids = self.repository.get_usable_admin_ids(
            db, admin_role.id, self._utc_now()
        )
        if usable_ids:
            self._block(
                db,
                actor_user_id=actor_user_id,
                target_user_id=None,
                operation="DEACTIVATE_ADMIN_ROLE",
            )

    def _block(
        self,
        db: Session,
        *,
        actor_user_id: UUID | None,
        target_user_id: UUID | None,
        operation: str,
    ) -> None:
        self.audit_service.record_event(
            db,
            event_type=SecurityAuditService.ADMIN_SAFETY_BLOCKED,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            details={"operation": operation},
        )
        db.commit()
        raise SecurityConflictException(self.BLOCK_MESSAGE)
