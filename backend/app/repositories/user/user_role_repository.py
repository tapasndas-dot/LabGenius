from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user.user_role import UserRole
from app.repositories.base_repository import BaseRepository


class UserRoleRepository(BaseRepository[UserRole]):
    """
    Repository for User-Role assignments.
    """

    def __init__(self):
        super().__init__(UserRole)

    def get_by_user(
        self,
        db: Session,
        user_id: UUID,
    ):
        return (
            db.query(UserRole)
            .filter(
                UserRole.user_id == user_id,
            )
            .all()
        )

    def get_assignment(
        self,
        db: Session,
        user_id: UUID,
        role_id: UUID,
    ):
        return (
            db.query(UserRole)
            .filter(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
            )
            .first()
        )

    def get_active_by_user(
        self,
        db: Session,
        user_id: UUID,
    ):
        return (
            db.query(UserRole)
            .filter(
                UserRole.user_id == user_id,
                UserRole.is_active.is_(True),
            )
            .all()
        )

    def delete_assignment(
        self,
        db: Session,
        assignment: UserRole,
    ):
        return self.delete(
            db,
            assignment,
        )