from enum import StrEnum
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.request_context import get_request_context
from app.core.sanitization import sanitize
from app.models.audit_event import AuditEvent
from app.repositories.audit_repository import AuditRepository
from app.services.organization_scope_service import AccessScope, OrganizationScopeService


class AuditAction(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    ACTIVATE = "ACTIVATE"
    DEACTIVATE = "DEACTIVATE"
    ASSIGN = "ASSIGN"
    UNASSIGN = "UNASSIGN"
    APPROVE = "APPROVE"
    RETIRE = "RETIRE"
    SUPERSEDE = "SUPERSEDE"
    CANCEL = "CANCEL"


class AuditService:
    def __init__(self) -> None:
        self.repository = AuditRepository()
        self.scope_service = OrganizationScopeService()

    @staticmethod
    def snapshot(value: Any, fields: list[str] | tuple[str, ...] | None = None) -> dict:
        if isinstance(value, dict):
            raw = value
        else:
            table = getattr(value, "__table__", None)
            names = fields or (
                tuple(c.key for c in table.columns)
                if table is not None else tuple(vars(value).keys())
            )
            raw = {name: getattr(value, name, None) for name in names}
        return sanitize(raw)

    @staticmethod
    def changes(before: dict, after: dict) -> dict:
        clean_before, clean_after = sanitize(before), sanitize(after)
        return {
            key: {"before": clean_before.get(key), "after": clean_after.get(key)}
            for key in clean_before.keys() | clean_after.keys()
            if clean_before.get(key) != clean_after.get(key)
        }

    def record_action(self, db: Session, *, action: str, entity_type: str,
                      entity_id: UUID | None = None, actor=None, changes=None,
                      owner=None, reason: str | None = None, source: str = "HTTP") -> AuditEvent:
        context = get_request_context()
        owner = owner or actor
        request_id = UUID(context.request_id) if context.request_id else None
        actor_id = getattr(actor, "id", actor if isinstance(actor, UUID) else None)
        event = AuditEvent(
            actor_user_id=actor_id, action=str(action).upper(),
            entity_type=entity_type, entity_id=entity_id,
            organization_id=getattr(owner, "organization_id", None),
            business_unit_id=getattr(owner, "business_unit_id", None),
            division_id=getattr(owner, "division_id", None),
            department_id=getattr(owner, "department_id", None),
            request_id=request_id, source_ip=context.source_ip,
            changes=sanitize(changes), reason=reason, source=source,
        )
        return self.repository.add(db, event)

    def record_create(self, db: Session, *, entity, actor, owner=None, reason=None):
        return self.record_action(db, action=AuditAction.CREATE,
            entity_type=type(entity).__name__, entity_id=entity.id, actor=actor,
            owner=owner or entity, changes={"created": self.snapshot(entity)}, reason=reason)

    def record_update(self, db: Session, *, entity, actor, before: dict, owner=None,
                      action: str = AuditAction.UPDATE, reason=None):
        return self.record_action(db, action=action, entity_type=type(entity).__name__,
            entity_id=entity.id, actor=actor, owner=owner or entity,
            changes=self.changes(before, self.snapshot(entity)), reason=reason)

    def record_delete(self, db: Session, *, entity, actor, before: dict, owner=None, reason=None):
        return self.record_action(db, action=AuditAction.DELETE,
            entity_type=type(entity).__name__, entity_id=entity.id, actor=actor,
            owner=owner or entity, changes={"deleted": sanitize(before)}, reason=reason)

    def scoped_query(self, db: Session, actor):
        query = self.repository.query(db)
        scope = self.scope_service.resolve_scope(actor, "audit.view")
        if scope == AccessScope.ORGANIZATION:
            return query.filter(AuditEvent.organization_id == actor.organization_id)
        if scope == AccessScope.BUSINESS_UNIT:
            return query.filter(AuditEvent.business_unit_id == actor.business_unit_id)
        if scope == AccessScope.DIVISION:
            return query.filter(AuditEvent.division_id == actor.division_id)
        if scope == AccessScope.DEPARTMENT:
            return query.filter(AuditEvent.department_id == actor.department_id)
        return query.filter(AuditEvent.actor_user_id == actor.id)

    def list(self, db: Session, actor, *, limit=100, offset=0, **filters):
        query = self.repository.apply_filters(self.scoped_query(db, actor), **filters)
        return query.order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc()).offset(offset).limit(limit).all()

    def get(self, db: Session, actor, event_id: UUID):
        event = self.scoped_query(db, actor).filter(AuditEvent.id == event_id).first()
        if event is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit event not found.")
        return event
