from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.schemas.business.manufacturer import ManufacturerCreate, ManufacturerResponse, ManufacturerUpdate
from app.schemas.business.shared import VersionRequest
from app.services.business.manufacturer_service import ManufacturerService

router = APIRouter(); service = ManufacturerService()

@router.get("", response_model=list[ManufacturerResponse])
def list_manufacturers(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), search: str | None = None,
                       is_active: bool | None = None, db: Session = Depends(get_db), actor=Depends(require_permission("manufacturer.view"))):
    return service.list_scoped(db, actor, "manufacturer.view", limit=limit, offset=offset, search=search, is_active=is_active)

@router.get("/{manufacturer_id}", response_model=ManufacturerResponse)
def get_manufacturer(manufacturer_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("manufacturer.view"))):
    return service.get_scoped(db, manufacturer_id, actor, "manufacturer.view")

@router.post("", response_model=ManufacturerResponse, status_code=201)
def create_manufacturer(payload: ManufacturerCreate, db: Session = Depends(get_db), actor=Depends(require_permission("manufacturer.create"))):
    return service.create_scoped(db, actor, payload.model_dump())

@router.put("/{manufacturer_id}", response_model=ManufacturerResponse)
def update_manufacturer(manufacturer_id: UUID, payload: ManufacturerUpdate, db: Session = Depends(get_db), actor=Depends(require_permission("manufacturer.update"))):
    return service.update_for_actor(db, actor, manufacturer_id, payload.version, payload.model_dump(exclude_unset=True, exclude={"version"}))

@router.put("/{manufacturer_id}/activate", response_model=ManufacturerResponse)
def activate_manufacturer(manufacturer_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("manufacturer.update"))):
    return service.set_active_scoped(db, actor, manufacturer_id, payload.version, True, "manufacturer.update")

@router.put("/{manufacturer_id}/deactivate", response_model=ManufacturerResponse)
def deactivate_manufacturer(manufacturer_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("manufacturer.update"))):
    return service.set_active_scoped(db, actor, manufacturer_id, payload.version, False, "manufacturer.update")

@router.delete("/{manufacturer_id}", status_code=204)
def delete_manufacturer(manufacturer_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("manufacturer.delete"))):
    service.delete_scoped(db, actor, manufacturer_id, payload.version, "manufacturer.delete")
