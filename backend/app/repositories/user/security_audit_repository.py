from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user.login_history import LoginHistory
from app.models.user.security_event import SecurityEvent


class SecurityAuditRepository:
    """Persistence and read queries for append-only security audit data."""

    def add_login_history(self, db: Session, record: LoginHistory) -> LoginHistory:
        db.add(record)
        return record

    def add_security_event(self, db: Session, event: SecurityEvent) -> SecurityEvent:
        db.add(event)
        return event

    def list_login_history(
        self, db: Session, user_id: UUID | None = None, limit: int = 100, offset: int = 0
    ) -> list[LoginHistory]:
        query = db.query(LoginHistory)
        if user_id is not None:
            query = query.filter(LoginHistory.user_id == user_id)
        return (
            query.order_by(LoginHistory.event_timestamp.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def list_security_events(
        self, db: Session, user_id: UUID | None = None, limit: int = 100, offset: int = 0
    ) -> list[SecurityEvent]:
        query = db.query(SecurityEvent)
        if user_id is not None:
            query = query.filter(
                (SecurityEvent.target_user_id == user_id)
                | (SecurityEvent.actor_user_id == user_id)
            )
        return (
            query.order_by(SecurityEvent.event_timestamp.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
