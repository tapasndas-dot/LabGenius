from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.user.role_repository import RoleRepository
from app.schemas.role import (
    RoleCreate,
    RoleStatusUpdate,
    RoleUpdate,
)


class RoleService:
    """
    Business logic for role administration.
    """

    def __init__(self):
        self.repository = RoleRepository()

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

        return self.repository.create(
            db,
            role,
        )

    def update(
        self,
        db: Session,
        role,
        data: RoleUpdate,
    ):
        if data.role_name is not None:
            role.role_name = data.role_name

        if data.description is not None:
            role.description = data.description

        return self.repository.update(
            db,
            role,
        )

    def update_status(
        self,
        db: Session,
        role_id: UUID,
        data: RoleStatusUpdate,
    ):
        role = self.get(
            db,
            role_id,
        )

        role.is_active = data.is_active

        return self.repository.update(
            db,
            role,
        )