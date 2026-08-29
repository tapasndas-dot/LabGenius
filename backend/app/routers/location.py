from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.models.business.location import LocationType
from app.schemas.business.location import LocationCreate, LocationResponse, LocationUpdate
from app.schemas.business.shared import VersionRequest
from app.services.business.location_service import LocationService

router = APIRouter()
service = LocationService()


@router.get("", response_model=list[LocationResponse])
def list_locations(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
                   search: str | None = None, is_active: bool | None = None,
                   parent_location_id: UUID | None = None, location_type: LocationType | None = None,
                   db: Session = Depends(get_db), actor=Depends(require_permission("location.view"))):
    return service.list_scoped(db, actor, "location.view", limit=limit, offset=offset,
        search=search, is_active=is_active, parent_location_id=parent_location_id,
        location_type=location_type)


@router.get("/{location_id}", response_model=LocationResponse)
def get_location(location_id: UUID, db: Session = Depends(get_db),
                 actor=Depends(require_permission("location.view"))):
    return service.get_scoped(db, location_id, actor, "location.view")


@router.post("", response_model=LocationResponse, status_code=201)
def create_location(payload: LocationCreate, db: Session = Depends(get_db),
                    actor=Depends(require_permission("location.create"))):
    return service.create_scoped(db, actor, payload.model_dump())


@router.put("/{location_id}", response_model=LocationResponse)
def update_location(location_id: UUID, payload: LocationUpdate, db: Session = Depends(get_db),
                    actor=Depends(require_permission("location.update"))):
    values = payload.model_dump(exclude_unset=True, exclude={"version"})
    return service.update_for_actor(db, actor, location_id, payload.version, values)


@router.put("/{location_id}/activate", response_model=LocationResponse)
def activate_location(location_id: UUID, payload: VersionRequest, db: Session = Depends(get_db),
                      actor=Depends(require_permission("location.update"))):
    return service.set_active_scoped(db, actor, location_id, payload.version, True, "location.update")


@router.put("/{location_id}/deactivate", response_model=LocationResponse)
def deactivate_location(location_id: UUID, payload: VersionRequest, db: Session = Depends(get_db),
                        actor=Depends(require_permission("location.update"))):
    return service.set_active_scoped(db, actor, location_id, payload.version, False, "location.update")


@router.delete("/{location_id}", status_code=204)
def delete_location(location_id: UUID, payload: VersionRequest, db: Session = Depends(get_db),
                    actor=Depends(require_permission("location.delete"))):
    service.delete_scoped(db, actor, location_id, payload.version, "location.delete")
