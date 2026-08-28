from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user.user import User


class SecurityRepository:
    """
    Repository for user security state.
    """

    def get_user(
        self,
        db: Session,
        user_id: UUID,
    ) -> User | None:
        return (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

    def save(
        self,
        db: Session,
        user: User,
    ) -> User:
        db.add(user)
        db.flush()
        return user

    def record_login_success(
        self,
        db: Session,
        user: User,
        login_time: datetime,
    ) -> User:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = login_time

        return self.save(
            db,
            user,
        )

    def record_login_failure(
        self,
        db: Session,
        user: User,
        failed_attempts: int,
        locked_until: datetime | None,
    ) -> User:
        user.failed_login_attempts = failed_attempts
        user.locked_until = locked_until

        return self.save(
            db,
            user,
        )
