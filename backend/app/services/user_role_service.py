from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user.user_role import UserRole
from app.repositories.user.user_role_repository import (
    UserRoleRepository,
)
from app.repositories.user.user_repository import UserRepository
from app.repositories.user.role_repository import RoleRepository
from app.schemas.user_role import UserRoleCreate
from app.services.user.admin_safety_service import AdminSafetyService
from app.services.organization_scope_service import OrganizationScopeService


class UserRoleService:
    """
    Business logic for User-Role administration.
    """

    def __init__(self):
        self.repository = UserRoleRepository()
        self.user_repository = UserRepository()
        self.role_repository = RoleRepository()
        self.admin_safety_service = AdminSafetyService()
        self.scope_service = OrganizationScopeService()

    def get_by_user(
        self,
        db: Session,
        user_id: UUID,
        actor,
    ):
        user = self.user_repository.get(
            db,
            user_id,
        )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        self.scope_service.ensure_can_access_user(actor, user, "user.view")

        return self.repository.get_by_user(
            db,
            user_id,
        )

    def assign_role(
        self,
        db: Session,
        user_id: UUID,
        data: UserRoleCreate,
        actor,
    ):
        user = self.user_repository.get(
            db,
            user_id,
        )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        self.scope_service.ensure_can_access_user(actor, user, "user.update")
        self.scope_service.ensure_scope_not_escalated(actor, "user.update", data.access_scope)

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign a role to an inactive user.",
            )

        role = self.role_repository.get(
            db,
            data.role_id,
        )

        if role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found.",
            )

        if not role.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign an inactive role.",
            )

        existing = self.repository.get_assignment(
            db,
            user_id,
            data.role_id,
        )

        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Role is already assigned to this user.",
            )

        assignment = UserRole(
            user_id=user_id,
            role_id=data.role_id,
            access_scope=data.access_scope,
        )

        return self.repository.create(
            db,
            assignment,
        )

    def remove_role(
        self,
        db: Session,
        user_id: UUID,
        role_id: UUID,
        actor,
    ):
        assignment = self.repository.get_assignment(
            db,
            user_id,
            role_id,
        )

        if assignment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User-role assignment not found.",
            )

        user = self.user_repository.get(db, user_id)
        self.scope_service.ensure_can_access_user(actor, user, "user.update")

        self.admin_safety_service.ensure_admin_assignment_can_be_removed(
            db,
            user_id,
            role_id,
            actor_user_id=actor.id,
        )

        self.repository.delete_assignment(
            db,
            assignment,
        )

        return {
            "message": "Role removed from user successfully."
        }
