from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.schemas.business.qc_method import TestCreate, TestResponse, TestUpdate
from app.schemas.business.shared import VersionRequest
from app.services.business.qc_api_service import test_api_service as service

router = APIRouter()

@router.get("", response_model=list[TestResponse])
def list_tests(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), search: str | None = None, is_active: bool | None = None, category: str | None = None, db: Session = Depends(get_db), actor=Depends(require_permission("test.view"))):
    return service.list(db, actor, "test.view", limit=limit, offset=offset, search=search, is_active=is_active, test_category=category)

@router.post("", response_model=TestResponse, status_code=201)
def create_test(payload: TestCreate, db: Session = Depends(get_db), actor=Depends(require_permission("test.create"))):
    return service.create(db, actor, "test.create", payload.model_dump())

@router.get("/{test_id}", response_model=TestResponse)
def get_test(test_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("test.view"))):
    return service.get(db, actor, test_id, "test.view")

@router.put("/{test_id}", response_model=TestResponse)
def update_test(test_id: UUID, payload: TestUpdate, db: Session = Depends(get_db), actor=Depends(require_permission("test.update"))):
    return service.update(db, actor, test_id, payload.version, "test.update", payload.model_dump(exclude_unset=True, exclude={"version"}))

@router.post("/{test_id}/activate", response_model=TestResponse)
def activate_test(test_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("test.update"))):
    return service.set_active(db, actor, test_id, payload.version, "test.update", True)

@router.post("/{test_id}/deactivate", response_model=TestResponse)
def deactivate_test(test_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("test.update"))):
    return service.set_active(db, actor, test_id, payload.version, "test.update", False)

@router.delete("/{test_id}", status_code=204)
def delete_test(test_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("test.delete"))):
    service.delete(db, actor, test_id, payload.version, "test.delete")
