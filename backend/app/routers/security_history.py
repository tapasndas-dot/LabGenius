from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.schemas.user.security_audit import LoginHistoryResponse, SecurityEventResponse
from app.services.user.security_audit_service import SecurityAuditService


router = APIRouter()
service = SecurityAuditService()
can_view_security_history = require_permission("user.view")


@router.get("/login-history", response_model=list[LoginHistoryResponse])
def list_login_history(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(can_view_security_history),
):
    return service.list_login_history(db, limit=limit, offset=offset)


@router.get("/login-history/{user_id}", response_model=list[LoginHistoryResponse])
def list_user_login_history(
    user_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(can_view_security_history),
):
    return service.list_login_history(db, user_id=user_id, limit=limit, offset=offset)


@router.get("/events", response_model=list[SecurityEventResponse])
def list_security_events(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(can_view_security_history),
):
    return service.list_security_events(db, limit=limit, offset=offset)


@router.get("/events/{user_id}", response_model=list[SecurityEventResponse])
def list_user_security_events(
    user_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(can_view_security_history),
):
    return service.list_security_events(db, user_id=user_id, limit=limit, offset=offset)
