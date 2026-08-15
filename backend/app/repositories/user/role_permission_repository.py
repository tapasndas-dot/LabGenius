from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user.role_permission import RolePermission
from app.repositories.base_repository import BaseRepository


class RolePermissionRepository(
    BaseRepository[RolePermission]
):
    """
    Repository for role-permission assignments.
    """

    def __init__(self):
        super().__init__(RolePermission)

    def get_assignment(
        self,
        db: Session,
        role_id: UUID,
        permission_id: UUID,
    ):
        return (
            db.query(RolePermission)
            .filter(
                RolePermission.role_id == role_id,
                RolePermission.permission_id
                == permission_id,
            )
            .first()
        )

    def get_by_role(
        self,
        db: Session,
        role_id: UUID,
    ):
        return (
            db.query(RolePermission)
            .filter(
                RolePermission.role_id == role_id,
            )
            .all()
        )

    def get_by_permission(
        self,
        db: Session,
        permission_id: UUID,
    ):
        return (
            db.query(RolePermission)
            .filter(
                RolePermission.permission_id
                == permission_id,
            )
            .all()
        )

    def delete_assignment(
        self,
        db: Session,
        assignment: RolePermission,
    ):
        db.delete(assignment)
        db.commit()