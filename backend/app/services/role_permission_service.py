from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user.role import Role
from app.models.user.permission import Permission
from app.models.user.role_permission import RolePermission

from app.repositories.user.role_permission_repository import (
    RolePermissionRepository,
)

from app.schemas.role_permission import (
    RolePermissionCreate,
)


class RolePermissionService:
    """
    Business logic for role-permission administration.
    """

    def __init__(self):
        self.repository = RolePermissionRepository()

    def get_by_role(
        self,
        db: Session,
        role_id: UUID,
    ):
        return self.repository.get_by_role(
            db,
            role_id,
        )

    def assign_permission(
        self,
        db: Session,
        role_id: UUID,
        data: RolePermissionCreate,
    ):
        role = (
            db.query(Role)
            .filter(Role.id == role_id)
            .first()
        )

        if role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found.",
            )

        if not role.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign permission to an inactive role.",
            )

        permission = (
            db.query(Permission)
            .filter(
                Permission.id == data.permission_id,
            )
            .first()
        )

        if permission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found.",
            )

        if not permission.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign an inactive permission.",
            )

        existing = self.repository.get_assignment(
            db,
            role_id,
            data.permission_id,
        )

        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Permission is already assigned to this role.",
            )

        assignment = RolePermission(
            role_id=role_id,
            permission_id=data.permission_id,
        )

        return self.repository.create(
            db,
            assignment,
        )

    def remove_permission(
        self,
        db: Session,
        role_id: UUID,
        permission_id: UUID,
    ):
        assignment = self.repository.get_assignment(
            db,
            role_id,
            permission_id,
        )

        if assignment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role-permission assignment not found.",
            )

        self.repository.delete_assignment(
            db,
            assignment,
        )

        return {
            "message": "Permission removed from role successfully."
        }