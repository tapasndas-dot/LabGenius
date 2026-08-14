from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.user.permission_repository import (
    PermissionRepository,
)
from app.schemas.permission import PermissionStatusUpdate


class PermissionService:
    """
    Business logic for permission administration.
    """

    def __init__(self):
        self.repository = PermissionRepository()

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
        permission_id: UUID,
    ):
        permission = self.repository.get(
            db,
            permission_id,
        )

        if permission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found.",
            )

        return permission

    def get_by_code(
        self,
        db: Session,
        permission_code: str,
    ):
        permission = self.repository.get_by_code(
            db,
            permission_code,
        )

        if permission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found.",
            )

        return permission

    def update_status(
        self,
        db: Session,
        permission_id: UUID,
        update: PermissionStatusUpdate,
    ):
        permission = self.get(
            db,
            permission_id,
        )

        permission.is_active = update.is_active

        return self.repository.update(
            db,
            permission,
        )