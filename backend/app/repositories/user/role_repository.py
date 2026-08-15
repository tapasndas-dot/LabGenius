from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user.role import Role
from app.repositories.base_repository import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """
    Repository for security roles.
    """

    def __init__(self):
        super().__init__(Role)

    def get_by_code(
        self,
        db: Session,
        role_code: str,
    ):
        return (
            db.query(Role)
            .filter(
                Role.role_code == role_code
            )
            .first()
        )

    def get_active(
        self,
        db: Session,
    ):
        return (
            db.query(Role)
            .filter(
                Role.is_active.is_(True)
            )
            .order_by(Role.role_code)
            .all()
        )

    def get_all_ordered(
        self,
        db: Session,
    ):
        return (
            db.query(Role)
            .order_by(Role.role_code)
            .all()
        )

    def get_with_permissions(
        self,
        db: Session,
        role_id: UUID,
    ):
        return (
            db.query(Role)
            .filter(Role.id == role_id)
            .first()
        )