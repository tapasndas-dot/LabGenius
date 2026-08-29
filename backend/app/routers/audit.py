from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.schemas.audit import AuditEventResponse
from app.services.audit_service import AuditService


router = APIRouter()
service = AuditService()
can_view_audit = require_permission("audit.view")


@router.get("/events", response_model=list[AuditEventResponse])
def list_audit_events(
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(can_view_audit),
):
    return service.list(
        db, current_user, entity_type=entity_type, entity_id=entity_id,
        actor_user_id=actor_user_id, action=action, date_from=date_from,
        date_to=date_to, limit=limit, offset=offset,
    )


@router.get("/events/{event_id}", response_model=AuditEventResponse)
def get_audit_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(can_view_audit),
):
    return service.get(db, current_user, event_id)
