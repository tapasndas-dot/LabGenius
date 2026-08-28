from datetime import datetime
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.user.role import Role
from app.models.user.user import User
from app.models.user.user_role import UserRole


class AdminSafetyRepository:
    """Serialized queries used by last-active-ADMIN safeguards."""

    def lock_admin_role(self, db: Session) -> Role | None:
        return (
            db.query(Role)
            .filter(Role.role_code == "ADMIN")
            .with_for_update()
            .first()
        )

    def get_usable_admin_ids(
        self,
        db: Session,
        admin_role_id: UUID,
        now: datetime,
    ) -> set[UUID]:
        rows = (
            db.query(User.id)
            .join(UserRole, UserRole.user_id == User.id)
            .filter(
                UserRole.role_id == admin_role_id,
                UserRole.is_active.is_(True),
                User.is_active.is_(True),
                User.account_status != "INACTIVE",
                or_(
                    User.account_status != "LOCKED",
                    User.locked_until.is_not(None) & (User.locked_until <= now),
                ),
            )
            .all()
        )
        return {row[0] for row in rows}
