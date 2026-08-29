from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.user.role_repository import RoleRepository
from app.schemas.role import (
    RoleCreate,
    RoleStatusUpdate,
    RoleUpdate,
)
from app.services.user.admin_safety_service import AdminSafetyService
from app.services.audit_service import AuditAction, AuditService


class RoleService:
    """
    Business logic for role administration.
    """

    def __init__(self):
        self.repository = RoleRepository()
        self.admin_safety_service = AdminSafetyService()
        self.audit_service = AuditService()

    def get_all(
        self,
        db: Session,
    ):
        return self.repository.get_all_ordered(db)

    def get_active(
        self,
        db: Session,
    ):
        return self.repository.get_active(db)

    def get(
        self,
        db: Session,
        role_id: UUID,
    ):
        role = self.repository.get(
            db,
            role_id,
        )

        if role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found.",
            )

        return role

    def get_by_code(
        self,
        db: Session,
        role_code: str,
    ):
        role = self.repository.get_by_code(
            db,
            role_code,
        )

        if role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found.",
            )

        return role

    def create(
        self,
        db: Session,
        data: RoleCreate,
        actor=None,
    ):
        existing = self.repository.get_by_code(
            db,
            data.role_code,
        )

        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Role code '{data.role_code}' "
                    "already exists."
                ),
            )

        role = self.repository.model(
            role_code=data.role_code,
            role_name=data.role_name,
            description=data.description,
        )

        db.add(role)
        db.flush()
        self.audit_service.record_create(db, entity=role, actor=actor, owner=actor)
        db.commit()
        db.refresh(role)
        return role

    def update(
        self,
        db: Session,
        role,
        data: RoleUpdate,
        actor=None,
    ):
        before = self.audit_service.snapshot(role)
        if data.role_name is not None:
            role.role_name = data.role_name

        if data.description is not None:
            role.description = data.description

        self.audit_service.record_update(db, entity=role, actor=actor, before=before, owner=actor)
        db.commit()
        db.refresh(role)
        return role

    def update_status(
        self,
        db: Session,
        role_id: UUID,
        data: RoleStatusUpdate,
        actor_user_id: UUID | None = None,
        actor=None,
    ):
        role = self.get(
            db,
            role_id,
        )

        if not data.is_active:
            self.admin_safety_service.ensure_role_can_be_deactivated(
                db,
                role.id,
                actor_user_id=actor_user_id,
            )

        before = self.audit_service.snapshot(role)
        role.is_active = data.is_active
        action = AuditAction.ACTIVATE if data.is_active else AuditAction.DEACTIVATE
        self.audit_service.record_update(db, entity=role, actor=actor, before=before,
                                         owner=actor, action=action)
        db.commit()
        db.refresh(role)
        return role
