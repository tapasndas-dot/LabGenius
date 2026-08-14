from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user.permission import Permission
from app.repositories.base_repository import BaseRepository


class PermissionRepository(BaseRepository[Permission]):
    """
    Repository for application permissions.
    """

    def __init__(self):
        super().__init__(Permission)

    def get_by_code(
        self,
        db: Session,
        permission_code: str,
    ):
        return (
            db.query(Permission)
            .filter(
                Permission.permission_code
                == permission_code
            )
            .first()
        )

    def get_active(
        self,
        db: Session,
    ):
        return (
            db.query(Permission)
            .filter(
                Permission.is_active.is_(True)
            )
            .order_by(
                Permission.permission_code
            )
            .all()
        )

    def get_all_ordered(
        self,
        db: Session,
    ):
        return (
            db.query(Permission)
            .order_by(
                Permission.permission_code
            )
            .all()
        )