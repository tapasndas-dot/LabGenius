from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.schemas.business.shared import VersionRequest
from app.schemas.business.stability import (
    StabilityProtocolConditionCreate, StabilityProtocolConditionResponse, StabilityProtocolConditionUpdate,
    StabilityProtocolCreate, StabilityProtocolResponse, StabilityProtocolTimepointCreate,
    StabilityProtocolTimepointResponse, StabilityProtocolTimepointUpdate, StabilityProtocolUpdate,
    StabilityProtocolVersionCreate, StabilityProtocolVersionResponse, StabilityProtocolVersionUpdate,
)
from app.services.business.stability_api_service import stability_protocol_api_service, stability_protocol_tree_api_service


router = APIRouter()
protocols = stability_protocol_api_service
tree = stability_protocol_tree_api_service


@router.get("", response_model=list[StabilityProtocolResponse])
def list_stability_protocols(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.view"))): return protocols.list(db, actor, "stability_protocol.view", limit=limit, offset=offset)

@router.post("", response_model=StabilityProtocolResponse, status_code=201)
def create_stability_protocol(payload: StabilityProtocolCreate, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.create"))): return protocols.create(db, actor, "stability_protocol.create", payload.model_dump())

@router.get("/{protocol_id}", response_model=StabilityProtocolResponse)
def get_stability_protocol(protocol_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.view"))): return protocols.get(db, actor, protocol_id, "stability_protocol.view")

@router.put("/{protocol_id}", response_model=StabilityProtocolResponse)
def update_stability_protocol(protocol_id: UUID, payload: StabilityProtocolUpdate, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.update"))): return protocols.update(db, actor, protocol_id, payload.version, "stability_protocol.update", payload.model_dump(exclude_unset=True, exclude={"version"}))

@router.post("/{protocol_id}/activate", response_model=StabilityProtocolResponse)
def activate_stability_protocol(protocol_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.update"))): return protocols.set_active(db, actor, protocol_id, payload.version, "stability_protocol.update", True)

@router.post("/{protocol_id}/deactivate", response_model=StabilityProtocolResponse)
def deactivate_stability_protocol(protocol_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.update"))): return protocols.set_active(db, actor, protocol_id, payload.version, "stability_protocol.update", False)

@router.delete("/{protocol_id}", status_code=204)
def delete_stability_protocol(protocol_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.delete"))): protocols.delete(db, actor, protocol_id, payload.version, "stability_protocol.delete")

@router.get("/{protocol_id}/versions", response_model=list[StabilityProtocolVersionResponse])
def list_stability_protocol_versions(protocol_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.view"))): return tree.list_versions(db, actor, protocol_id, "stability_protocol.view")

@router.post("/{protocol_id}/versions", response_model=StabilityProtocolVersionResponse, status_code=201)
def create_stability_protocol_version(protocol_id: UUID, payload: StabilityProtocolVersionCreate, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.create"))): return tree.create_version(db, actor, protocol_id, "stability_protocol.create", payload.model_dump())

@router.get("/{protocol_id}/versions/{version_id}", response_model=StabilityProtocolVersionResponse)
def get_stability_protocol_version(protocol_id: UUID, version_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.view"))): return tree.version(db, actor, protocol_id, version_id, "stability_protocol.view")

@router.put("/{protocol_id}/versions/{version_id}", response_model=StabilityProtocolVersionResponse)
def update_stability_protocol_version(protocol_id: UUID, version_id: UUID, payload: StabilityProtocolVersionUpdate, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.update"))): return tree.update_version(db, actor, protocol_id, version_id, payload.version, "stability_protocol.update", payload.model_dump(exclude_unset=True, exclude={"version"}))

def _version_lifecycle(protocol_id, version_id, payload, db, actor, target): return tree.lifecycle(db, actor, protocol_id, version_id, payload.version, "stability_protocol.update", target)

@router.post("/{protocol_id}/versions/{version_id}/approve", response_model=StabilityProtocolVersionResponse)
def approve_stability_protocol_version(protocol_id: UUID, version_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.update"))): return _version_lifecycle(protocol_id, version_id, payload, db, actor, "APPROVED")

@router.post("/{protocol_id}/versions/{version_id}/retire", response_model=StabilityProtocolVersionResponse)
def retire_stability_protocol_version(protocol_id: UUID, version_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.update"))): return _version_lifecycle(protocol_id, version_id, payload, db, actor, "RETIRED")

@router.post("/{protocol_id}/versions/{version_id}/supersede", response_model=StabilityProtocolVersionResponse)
def supersede_stability_protocol_version(protocol_id: UUID, version_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.update"))): return _version_lifecycle(protocol_id, version_id, payload, db, actor, "SUPERSEDED")

@router.get("/{protocol_id}/versions/{version_id}/conditions", response_model=list[StabilityProtocolConditionResponse])
def list_stability_protocol_conditions(protocol_id: UUID, version_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.view"))): return tree.list_conditions(db, actor, protocol_id, version_id, "stability_protocol.view")

@router.post("/{protocol_id}/versions/{version_id}/conditions", response_model=StabilityProtocolConditionResponse, status_code=201)
def create_stability_protocol_condition(protocol_id: UUID, version_id: UUID, payload: StabilityProtocolConditionCreate, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.create"))): return tree.create_condition(db, actor, protocol_id, version_id, "stability_protocol.create", payload.model_dump())

@router.get("/{protocol_id}/versions/{version_id}/conditions/{condition_id}", response_model=StabilityProtocolConditionResponse)
def get_stability_protocol_condition(protocol_id: UUID, version_id: UUID, condition_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.view"))): return tree.condition(db, actor, protocol_id, version_id, condition_id, "stability_protocol.view")

@router.put("/{protocol_id}/versions/{version_id}/conditions/{condition_id}", response_model=StabilityProtocolConditionResponse)
def update_stability_protocol_condition(protocol_id: UUID, version_id: UUID, condition_id: UUID, payload: StabilityProtocolConditionUpdate, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.update"))): return tree.update_condition(db, actor, protocol_id, version_id, condition_id, payload.version, "stability_protocol.update", payload.model_dump(exclude_unset=True, exclude={"version"}))

@router.delete("/{protocol_id}/versions/{version_id}/conditions/{condition_id}", status_code=204)
def delete_stability_protocol_condition(protocol_id: UUID, version_id: UUID, condition_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.update"))): tree.delete_condition(db, actor, protocol_id, version_id, condition_id, payload.version, "stability_protocol.update")

@router.get("/{protocol_id}/versions/{version_id}/conditions/{condition_id}/timepoints", response_model=list[StabilityProtocolTimepointResponse])
def list_stability_protocol_timepoints(protocol_id: UUID, version_id: UUID, condition_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.view"))): return tree.list_timepoints(db, actor, protocol_id, version_id, condition_id, "stability_protocol.view")

@router.post("/{protocol_id}/versions/{version_id}/conditions/{condition_id}/timepoints", response_model=StabilityProtocolTimepointResponse, status_code=201)
def create_stability_protocol_timepoint(protocol_id: UUID, version_id: UUID, condition_id: UUID, payload: StabilityProtocolTimepointCreate, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.create"))): return tree.create_timepoint(db, actor, protocol_id, version_id, condition_id, "stability_protocol.create", payload.model_dump())

@router.get("/{protocol_id}/versions/{version_id}/conditions/{condition_id}/timepoints/{timepoint_id}", response_model=StabilityProtocolTimepointResponse)
def get_stability_protocol_timepoint(protocol_id: UUID, version_id: UUID, condition_id: UUID, timepoint_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.view"))): return tree.timepoint(db, actor, protocol_id, version_id, condition_id, timepoint_id, "stability_protocol.view")

@router.put("/{protocol_id}/versions/{version_id}/conditions/{condition_id}/timepoints/{timepoint_id}", response_model=StabilityProtocolTimepointResponse)
def update_stability_protocol_timepoint(protocol_id: UUID, version_id: UUID, condition_id: UUID, timepoint_id: UUID, payload: StabilityProtocolTimepointUpdate, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.update"))): return tree.update_timepoint(db, actor, protocol_id, version_id, condition_id, timepoint_id, payload.version, "stability_protocol.update", payload.model_dump(exclude_unset=True, exclude={"version"}))

@router.delete("/{protocol_id}/versions/{version_id}/conditions/{condition_id}/timepoints/{timepoint_id}", status_code=204)
def delete_stability_protocol_timepoint(protocol_id: UUID, version_id: UUID, condition_id: UUID, timepoint_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("stability_protocol.update"))): tree.delete_timepoint(db, actor, protocol_id, version_id, condition_id, timepoint_id, payload.version, "stability_protocol.update")
