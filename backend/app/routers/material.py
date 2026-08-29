from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.models.business.material import MaterialType
from app.schemas.business.material import MaterialCreate, MaterialResponse, MaterialUpdate
from app.schemas.business.shared import VersionRequest
from app.services.business.material_service import MaterialService

router = APIRouter(); service = MaterialService()

@router.get("", response_model=list[MaterialResponse])
def list_materials(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), search: str | None = None,
                   is_active: bool | None = None, material_type: MaterialType | None = None, db: Session = Depends(get_db), actor=Depends(require_permission("material.view"))):
    return service.list_scoped(db, actor, "material.view", limit=limit, offset=offset, search=search, is_active=is_active, material_type=material_type)

@router.get("/{material_id}", response_model=MaterialResponse)
def get_material(material_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("material.view"))):
    return service.get_scoped(db, material_id, actor, "material.view")

@router.post("", response_model=MaterialResponse, status_code=201)
def create_material(payload: MaterialCreate, db: Session = Depends(get_db), actor=Depends(require_permission("material.create"))):
    return service.create_scoped(db, actor, payload.model_dump())

@router.put("/{material_id}", response_model=MaterialResponse)
def update_material(material_id: UUID, payload: MaterialUpdate, db: Session = Depends(get_db), actor=Depends(require_permission("material.update"))):
    return service.update_for_actor(db, actor, material_id, payload.version, payload.model_dump(exclude_unset=True, exclude={"version"}))

@router.put("/{material_id}/activate", response_model=MaterialResponse)
def activate_material(material_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("material.update"))):
    return service.set_active_scoped(db, actor, material_id, payload.version, True, "material.update")

@router.put("/{material_id}/deactivate", response_model=MaterialResponse)
def deactivate_material(material_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("material.update"))):
    return service.set_active_scoped(db, actor, material_id, payload.version, False, "material.update")

@router.delete("/{material_id}", status_code=204)
def delete_material(material_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("material.delete"))):
    service.delete_scoped(db, actor, material_id, payload.version, "material.delete")
