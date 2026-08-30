from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.models.business.qc_method import MethodVersionStatus
from app.schemas.business.qc_method import *
from app.schemas.business.shared import VersionRequest
from app.services.business.qc_api_service import MethodTreeAPIService, method_api_service

router = APIRouter(); tree = MethodTreeAPIService()

@router.get("", response_model=list[MethodResponse])
def list_methods(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), search: str | None = None, is_active: bool | None = None, db: Session = Depends(get_db), actor=Depends(require_permission("method.view"))):
    return method_api_service.list(db, actor, "method.view", limit=limit, offset=offset, search=search, is_active=is_active)

@router.post("", response_model=MethodResponse, status_code=201)
def create_method(payload: MethodCreate, db: Session = Depends(get_db), actor=Depends(require_permission("method.create"))): return method_api_service.create(db, actor, "method.create", payload.model_dump())

@router.get("/{method_id}", response_model=MethodResponse)
def get_method(method_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("method.view"))): return method_api_service.get(db, actor, method_id, "method.view")

@router.put("/{method_id}", response_model=MethodResponse)
def update_method(method_id: UUID, payload: MethodUpdate, db: Session = Depends(get_db), actor=Depends(require_permission("method.update"))): return method_api_service.update(db, actor, method_id, payload.version, "method.update", payload.model_dump(exclude_unset=True, exclude={"version"}))

@router.post("/{method_id}/activate", response_model=MethodResponse)
def activate_method(method_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("method.update"))): return method_api_service.set_active(db, actor, method_id, payload.version, "method.update", True)

@router.post("/{method_id}/deactivate", response_model=MethodResponse)
def deactivate_method(method_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("method.update"))): return method_api_service.set_active(db, actor, method_id, payload.version, "method.update", False)

@router.delete("/{method_id}", status_code=204)
def delete_method(method_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("method.delete"))): method_api_service.delete(db, actor, method_id, payload.version, "method.delete")

@router.get("/{method_id}/versions", response_model=list[MethodVersionResponse])
def list_versions(method_id: UUID, status: MethodVersionStatus | None = None, db: Session = Depends(get_db), actor=Depends(require_permission("method.view"))): return tree.list_versions(db, actor, method_id, "method.view", status)

@router.post("/{method_id}/versions", response_model=MethodVersionResponse, status_code=201)
def create_version(method_id: UUID, payload: MethodVersionCreate, db: Session = Depends(get_db), actor=Depends(require_permission("method.create"))): return tree.create_version(db, actor, method_id, "method.create", payload.model_dump())

@router.get("/{method_id}/versions/{version_id}", response_model=MethodVersionResponse)
def get_version(method_id: UUID, version_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("method.view"))): return tree.version(db, actor, method_id, version_id, "method.view")

@router.put("/{method_id}/versions/{version_id}", response_model=MethodVersionResponse)
def update_version(method_id: UUID, version_id: UUID, payload: MethodVersionUpdate, db: Session = Depends(get_db), actor=Depends(require_permission("method.update"))): return tree.update_version(db, actor, method_id, version_id, payload.version, "method.update", payload.model_dump(exclude_unset=True, exclude={"version"}))

def _lifecycle(method_id, version_id, payload, db, actor, target): return tree.lifecycle(db, actor, method_id, version_id, payload.version, "method.update", target)
@router.post("/{method_id}/versions/{version_id}/approve", response_model=MethodVersionResponse)
def approve_version(method_id: UUID, version_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("method.update"))): return _lifecycle(method_id, version_id, payload, db, actor, "APPROVED")
@router.post("/{method_id}/versions/{version_id}/retire", response_model=MethodVersionResponse)
def retire_version(method_id: UUID, version_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("method.update"))): return _lifecycle(method_id, version_id, payload, db, actor, "RETIRED")
@router.post("/{method_id}/versions/{version_id}/supersede", response_model=MethodVersionResponse)
def supersede_version(method_id: UUID, version_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("method.update"))): return _lifecycle(method_id, version_id, payload, db, actor, "SUPERSEDED")

@router.get("/{method_id}/versions/{version_id}/parameters", response_model=list[MethodParameterResponse])
def list_parameters(method_id: UUID, version_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("method.view"))): return tree.list_parameters(db, actor, method_id, version_id, "method.view")
@router.post("/{method_id}/versions/{version_id}/parameters", response_model=MethodParameterResponse, status_code=201)
def create_parameter(method_id: UUID, version_id: UUID, payload: MethodParameterCreate, db: Session = Depends(get_db), actor=Depends(require_permission("method.create"))): return tree.create_parameter(db, actor, method_id, version_id, "method.create", payload.model_dump())
@router.put("/{method_id}/versions/{version_id}/parameters/{parameter_id}", response_model=MethodParameterResponse)
def update_parameter(method_id: UUID, version_id: UUID, parameter_id: UUID, payload: MethodParameterUpdate, db: Session = Depends(get_db), actor=Depends(require_permission("method.update"))): return tree.update_parameter(db, actor, method_id, version_id, parameter_id, payload.version, "method.update", payload.model_dump(exclude_unset=True, exclude={"version"}))
@router.delete("/{method_id}/versions/{version_id}/parameters/{parameter_id}", status_code=204)
def delete_parameter(method_id: UUID, version_id: UUID, parameter_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("method.update"))): tree.delete_parameter(db, actor, method_id, version_id, parameter_id, payload.version, "method.update")
