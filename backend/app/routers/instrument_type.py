from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.schemas.business.instrument_type import InstrumentTypeCreate, InstrumentTypeResponse, InstrumentTypeUpdate
from app.schemas.business.shared import VersionRequest
from app.services.business.instrument_type_service import InstrumentTypeService

router = APIRouter(); service = InstrumentTypeService()

@router.get("", response_model=list[InstrumentTypeResponse])
def list_instrument_types(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), search: str | None = None,
                          is_active: bool | None = None, db: Session = Depends(get_db), actor=Depends(require_permission("instrument_type.view"))):
    return service.list_scoped(db, actor, "instrument_type.view", limit=limit, offset=offset, search=search, is_active=is_active)

@router.get("/{instrument_type_id}", response_model=InstrumentTypeResponse)
def get_instrument_type(instrument_type_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("instrument_type.view"))):
    return service.get_scoped(db, instrument_type_id, actor, "instrument_type.view")

@router.post("", response_model=InstrumentTypeResponse, status_code=201)
def create_instrument_type(payload: InstrumentTypeCreate, db: Session = Depends(get_db), actor=Depends(require_permission("instrument_type.create"))):
    return service.create_scoped(db, actor, payload.model_dump())

@router.put("/{instrument_type_id}", response_model=InstrumentTypeResponse)
def update_instrument_type(instrument_type_id: UUID, payload: InstrumentTypeUpdate, db: Session = Depends(get_db), actor=Depends(require_permission("instrument_type.update"))):
    return service.update_for_actor(db, actor, instrument_type_id, payload.version, payload.model_dump(exclude_unset=True, exclude={"version"}))

@router.put("/{instrument_type_id}/activate", response_model=InstrumentTypeResponse)
def activate_instrument_type(instrument_type_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("instrument_type.update"))):
    return service.set_active_scoped(db, actor, instrument_type_id, payload.version, True, "instrument_type.update")

@router.put("/{instrument_type_id}/deactivate", response_model=InstrumentTypeResponse)
def deactivate_instrument_type(instrument_type_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("instrument_type.update"))):
    return service.set_active_scoped(db, actor, instrument_type_id, payload.version, False, "instrument_type.update")

@router.delete("/{instrument_type_id}", status_code=204)
def delete_instrument_type(instrument_type_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("instrument_type.delete"))):
    service.delete_scoped(db, actor, instrument_type_id, payload.version, "instrument_type.delete")
