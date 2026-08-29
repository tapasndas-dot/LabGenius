from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent


class AuditRepository:
    def add(self, db: Session, event: AuditEvent) -> AuditEvent:
        db.add(event)
        return event

    def query(self, db: Session):
        return db.query(AuditEvent)

    def get(self, db: Session, event_id: UUID) -> AuditEvent | None:
        return self.query(db).filter(AuditEvent.id == event_id).first()

    def apply_filters(self, query, *, entity_type=None, entity_id=None,
                      actor_user_id=None, action=None, date_from: datetime | None = None,
                      date_to: datetime | None = None):
        if entity_type is not None:
            query = query.filter(AuditEvent.entity_type == entity_type)
        if entity_id is not None:
            query = query.filter(AuditEvent.entity_id == entity_id)
        if actor_user_id is not None:
            query = query.filter(AuditEvent.actor_user_id == actor_user_id)
        if action is not None:
            query = query.filter(AuditEvent.action == action.upper())
        if date_from is not None:
            query = query.filter(AuditEvent.occurred_at >= date_from)
        if date_to is not None:
            query = query.filter(AuditEvent.occurred_at <= date_to)
        return query
