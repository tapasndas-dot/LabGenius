from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.models.business.specification import SpecificationVersionStatus
from app.schemas.business.shared import VersionRequest
from app.schemas.business.specification import *
from app.services.business.qc_api_service import SpecificationTreeAPIService, specification_api_service

router = APIRouter(); tree = SpecificationTreeAPIService()

@router.get("", response_model=list[SpecificationResponse])
def list_specifications(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), search: str | None = None, material_id: UUID | None = None, is_active: bool | None = None, db: Session = Depends(get_db), actor=Depends(require_permission("specification.view"))): return specification_api_service.list(db, actor, "specification.view", limit=limit, offset=offset, search=search, material_id=material_id, is_active=is_active)
@router.post("", response_model=SpecificationResponse, status_code=201)
def create_specification(payload: SpecificationCreate, db: Session = Depends(get_db), actor=Depends(require_permission("specification.create"))): return specification_api_service.create(db, actor, "specification.create", payload.model_dump())
@router.get("/{specification_id}", response_model=SpecificationResponse)
def get_specification(specification_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("specification.view"))): return specification_api_service.get(db, actor, specification_id, "specification.view")
@router.put("/{specification_id}", response_model=SpecificationResponse)
def update_specification(specification_id: UUID, payload: SpecificationUpdate, db: Session = Depends(get_db), actor=Depends(require_permission("specification.update"))): return specification_api_service.update(db, actor, specification_id, payload.version, "specification.update", payload.model_dump(exclude_unset=True, exclude={"version"}))
@router.post("/{specification_id}/activate", response_model=SpecificationResponse)
def activate_specification(specification_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("specification.update"))): return specification_api_service.set_active(db, actor, specification_id, payload.version, "specification.update", True)
@router.post("/{specification_id}/deactivate", response_model=SpecificationResponse)
def deactivate_specification(specification_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("specification.update"))): return specification_api_service.set_active(db, actor, specification_id, payload.version, "specification.update", False)
@router.delete("/{specification_id}", status_code=204)
def delete_specification(specification_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("specification.delete"))): specification_api_service.delete(db, actor, specification_id, payload.version, "specification.delete")

@router.get("/{specification_id}/versions", response_model=list[SpecificationVersionResponse])
def list_versions(specification_id: UUID, status: SpecificationVersionStatus | None = None, db: Session = Depends(get_db), actor=Depends(require_permission("specification.view"))): return tree.list_versions(db, actor, specification_id, "specification.view", status)
@router.post("/{specification_id}/versions", response_model=SpecificationVersionResponse, status_code=201)
def create_version(specification_id: UUID, payload: SpecificationVersionCreate, db: Session = Depends(get_db), actor=Depends(require_permission("specification.create"))): return tree.create_version(db, actor, specification_id, "specification.create", payload.model_dump())
@router.get("/{specification_id}/versions/{version_id}", response_model=SpecificationVersionResponse)
def get_version(specification_id: UUID, version_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("specification.view"))): return tree.version(db, actor, specification_id, version_id, "specification.view")
@router.put("/{specification_id}/versions/{version_id}", response_model=SpecificationVersionResponse)
def update_version(specification_id: UUID, version_id: UUID, payload: SpecificationVersionUpdate, db: Session = Depends(get_db), actor=Depends(require_permission("specification.update"))): return tree.update_version(db, actor, specification_id, version_id, payload.version, "specification.update", payload.model_dump(exclude_unset=True, exclude={"version"}))

def _lifecycle(specification_id, version_id, payload, db, actor, target): return tree.lifecycle(db, actor, specification_id, version_id, payload.version, "specification.update", target)
@router.post("/{specification_id}/versions/{version_id}/approve", response_model=SpecificationVersionResponse)
def approve_version(specification_id: UUID, version_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("specification.update"))): return _lifecycle(specification_id, version_id, payload, db, actor, "APPROVED")
@router.post("/{specification_id}/versions/{version_id}/retire", response_model=SpecificationVersionResponse)
def retire_version(specification_id: UUID, version_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("specification.update"))): return _lifecycle(specification_id, version_id, payload, db, actor, "RETIRED")
@router.post("/{specification_id}/versions/{version_id}/supersede", response_model=SpecificationVersionResponse)
def supersede_version(specification_id: UUID, version_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("specification.update"))): return _lifecycle(specification_id, version_id, payload, db, actor, "SUPERSEDED")

@router.get("/{specification_id}/versions/{version_id}/tests", response_model=list[SpecificationTestResponse])
def list_tests(specification_id: UUID, version_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("specification.view"))): return tree.list_tests(db, actor, specification_id, version_id, "specification.view")
@router.post("/{specification_id}/versions/{version_id}/tests", response_model=SpecificationTestResponse, status_code=201)
def create_test(specification_id: UUID, version_id: UUID, payload: SpecificationTestCreate, db: Session = Depends(get_db), actor=Depends(require_permission("specification.create"))): return tree.create_test(db, actor, specification_id, version_id, "specification.create", payload.model_dump())
@router.put("/{specification_id}/versions/{version_id}/tests/{test_id}", response_model=SpecificationTestResponse)
def update_test(specification_id: UUID, version_id: UUID, test_id: UUID, payload: SpecificationTestUpdate, db: Session = Depends(get_db), actor=Depends(require_permission("specification.update"))): return tree.update_test(db, actor, specification_id, version_id, test_id, payload.version, "specification.update", payload.model_dump(exclude_unset=True, exclude={"version"}))
@router.delete("/{specification_id}/versions/{version_id}/tests/{test_id}", status_code=204)
def delete_test(specification_id: UUID, version_id: UUID, test_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("specification.update"))): tree.delete_test(db, actor, specification_id, version_id, test_id, payload.version, "specification.update")

@router.get("/{specification_id}/versions/{version_id}/tests/{test_id}/limits", response_model=list[SpecificationLimitResponse])
def list_limits(specification_id: UUID, version_id: UUID, test_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("specification.view"))): return tree.list_limits(db, actor, specification_id, version_id, test_id, "specification.view")
@router.post("/{specification_id}/versions/{version_id}/tests/{test_id}/limits", response_model=SpecificationLimitResponse, status_code=201)
def create_limit(specification_id: UUID, version_id: UUID, test_id: UUID, payload: SpecificationLimitCreate, db: Session = Depends(get_db), actor=Depends(require_permission("specification.create"))): return tree.create_limit(db, actor, specification_id, version_id, test_id, "specification.create", payload.model_dump())
@router.put("/{specification_id}/versions/{version_id}/tests/{test_id}/limits/{limit_id}", response_model=SpecificationLimitResponse)
def update_limit(specification_id: UUID, version_id: UUID, test_id: UUID, limit_id: UUID, payload: SpecificationLimitUpdate, db: Session = Depends(get_db), actor=Depends(require_permission("specification.update"))): return tree.update_limit(db, actor, specification_id, version_id, test_id, limit_id, payload.version, "specification.update", payload.model_dump(exclude_unset=True, exclude={"version"}))
@router.delete("/{specification_id}/versions/{version_id}/tests/{test_id}/limits/{limit_id}", status_code=204)
def delete_limit(specification_id: UUID, version_id: UUID, test_id: UUID, limit_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("specification.update"))): tree.delete_limit(db, actor, specification_id, version_id, test_id, limit_id, payload.version, "specification.update")
