from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.capabilities import require_capability
from app.dependencies.database import get_db
from app.schemas.business.instrument import (
    InstrumentCreate, InstrumentResponse, InstrumentUpdate,
)
from app.schemas.business.shared import VersionRequest
from app.services.business.instrument_service import InstrumentService


router = APIRouter(dependencies=[Depends(require_capability("INSTRUMENTS"))])
service = InstrumentService()


@router.get("", response_model=list[InstrumentResponse])
def list_instruments(
    limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
    search: str | None = None, is_active: bool | None = None,
    status: str | None = None, instrument_type_id: UUID | None = None,
    manufacturer_id: UUID | None = None, location_id: UUID | None = None,
    business_unit_id: UUID | None = None, division_id: UUID | None = None,
    department_id: UUID | None = None, db: Session = Depends(get_db),
    actor=Depends(require_permission("instrument.view")),
):
    return service.list_scoped(
        db, actor, "instrument.view", limit=limit, offset=offset, search=search,
        is_active=is_active, status=status, instrument_type_id=instrument_type_id,
        manufacturer_id=manufacturer_id, location_id=location_id,
        business_unit_id=business_unit_id, division_id=division_id,
        department_id=department_id,
    )


@router.get("/{instrument_id}", response_model=InstrumentResponse)
def get_instrument(
    instrument_id: UUID, db: Session = Depends(get_db),
    actor=Depends(require_permission("instrument.view")),
):
    return service.get_scoped(db, actor, instrument_id, "instrument.view")


@router.post("", response_model=InstrumentResponse, status_code=201)
def create_instrument(
    payload: InstrumentCreate, db: Session = Depends(get_db),
    actor=Depends(require_permission("instrument.create")),
):
    return service.create_scoped(db, actor, payload.model_dump())


@router.put("/{instrument_id}", response_model=InstrumentResponse)
def update_instrument(
    instrument_id: UUID, payload: InstrumentUpdate, db: Session = Depends(get_db),
    actor=Depends(require_permission("instrument.update")),
):
    return service.update_scoped(
        db, actor, instrument_id, payload.version,
        payload.model_dump(exclude_unset=True, exclude={"version"}),
    )


@router.put("/{instrument_id}/activate", response_model=InstrumentResponse)
def activate_instrument(
    instrument_id: UUID, payload: VersionRequest, db: Session = Depends(get_db),
    actor=Depends(require_permission("instrument.update")),
):
    return service.set_active_scoped(db, actor, instrument_id, payload.version, True)


@router.put("/{instrument_id}/deactivate", response_model=InstrumentResponse)
def deactivate_instrument(
    instrument_id: UUID, payload: VersionRequest, db: Session = Depends(get_db),
    actor=Depends(require_permission("instrument.update")),
):
    return service.set_active_scoped(db, actor, instrument_id, payload.version, False)


@router.delete("/{instrument_id}", status_code=204)
def delete_instrument(
    instrument_id: UUID, payload: VersionRequest, db: Session = Depends(get_db),
    actor=Depends(require_permission("instrument.delete")),
):
    service.delete_scoped(db, actor, instrument_id, payload.version)
