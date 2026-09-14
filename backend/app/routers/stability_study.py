from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.schemas.business.shared import VersionRequest
from app.schemas.business.stability import (
    StabilityPullCreateSampleRequest, StabilityPullMarkPulledRequest, StabilityPullResponse,
    StabilityStudyConditionCreate, StabilityStudyConditionResponse, StabilityStudyConditionUpdate,
    StabilityStudyCreate, StabilityStudyResponse, StabilityStudyUpdate,
)
from app.models.business.stability import StabilityPullStatus
from app.services.business.stability_api_service import stability_pull_api_service, stability_study_api_service


router = APIRouter()
studies = stability_study_api_service
pulls = stability_pull_api_service


@router.get("", response_model=list[StabilityStudyResponse])
def list_stability_studies(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db), actor=Depends(require_permission("stability_study.view"))): return studies.list(db, actor, "stability_study.view", limit=limit, offset=offset)

@router.post("", response_model=StabilityStudyResponse, status_code=201)
def create_stability_study(payload: StabilityStudyCreate, db: Session = Depends(get_db), actor=Depends(require_permission("stability_study.create"))): return studies.create(db, actor, "stability_study.create", payload.model_dump())

@router.get("/{study_id}", response_model=StabilityStudyResponse)
def get_stability_study(study_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("stability_study.view"))): return studies.get(db, actor, study_id, "stability_study.view")

@router.put("/{study_id}", response_model=StabilityStudyResponse)
def update_stability_study(study_id: UUID, payload: StabilityStudyUpdate, db: Session = Depends(get_db), actor=Depends(require_permission("stability_study.update"))): return studies.update(db, actor, study_id, payload.version, "stability_study.update", payload.model_dump(exclude_unset=True, exclude={"version"}))

def _study_lifecycle(study_id, payload, db, actor, permission, target): return studies.transition(db, actor, study_id, payload.version, permission, target)

@router.post("/{study_id}/activate", response_model=StabilityStudyResponse)
def activate_stability_study(study_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("stability_study.update"))): return _study_lifecycle(study_id, payload, db, actor, "stability_study.update", "ACTIVE")

@router.post("/{study_id}/complete", response_model=StabilityStudyResponse)
def complete_stability_study(study_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("stability_study.update"))): return _study_lifecycle(study_id, payload, db, actor, "stability_study.update", "COMPLETED")

@router.post("/{study_id}/cancel", response_model=StabilityStudyResponse)
def cancel_stability_study(study_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("stability_study.cancel"))): return _study_lifecycle(study_id, payload, db, actor, "stability_study.cancel", "CANCELLED")

@router.get("/{study_id}/conditions", response_model=list[StabilityStudyConditionResponse])
def list_stability_study_conditions(study_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("stability_study.view"))): return studies.list_conditions(db, actor, study_id, "stability_study.view")

@router.post("/{study_id}/conditions", response_model=StabilityStudyConditionResponse, status_code=201)
def create_stability_study_condition(study_id: UUID, payload: StabilityStudyConditionCreate, db: Session = Depends(get_db), actor=Depends(require_permission("stability_study.update"))): return studies.create_condition(db, actor, study_id, "stability_study.update", payload.model_dump())

@router.get("/{study_id}/conditions/{study_condition_id}", response_model=StabilityStudyConditionResponse)
def get_stability_study_condition(study_id: UUID, study_condition_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("stability_study.view"))): return studies.study_condition(db, actor, study_id, study_condition_id, "stability_study.view")

@router.put("/{study_id}/conditions/{study_condition_id}", response_model=StabilityStudyConditionResponse)
def update_stability_study_condition(study_id: UUID, study_condition_id: UUID, payload: StabilityStudyConditionUpdate, db: Session = Depends(get_db), actor=Depends(require_permission("stability_study.update"))): return studies.update_condition(db, actor, study_id, study_condition_id, payload.version, "stability_study.update", payload.model_dump(exclude_unset=True, exclude={"version"}))

@router.delete("/{study_id}/conditions/{study_condition_id}", status_code=204)
def delete_stability_study_condition(study_id: UUID, study_condition_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("stability_study.update"))): studies.delete_condition(db, actor, study_id, study_condition_id, payload.version, "stability_study.update")

@router.get("/{study_id}/pulls", response_model=list[StabilityPullResponse])
def list_stability_pulls(study_id: UUID, status: StabilityPullStatus | None = Query(None), study_condition_id: UUID | None = Query(None), scheduled_from: date | None = Query(None), scheduled_to: date | None = Query(None), limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db), actor=Depends(require_permission("stability_pull.view"))):
    return pulls.list(db, actor, study_id, "stability_pull.view", status=status, study_condition_id=study_condition_id, scheduled_from=scheduled_from, scheduled_to=scheduled_to, limit=limit, offset=offset)

@router.get("/{study_id}/pulls/{pull_id}", response_model=StabilityPullResponse)
def get_stability_pull(study_id: UUID, pull_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("stability_pull.view"))):
    return pulls.get(db, actor, study_id, pull_id, "stability_pull.view")

@router.post("/{study_id}/pulls/{pull_id}/mark-pulled", response_model=StabilityPullResponse)
def mark_stability_pull_pulled(study_id: UUID, pull_id: UUID, payload: StabilityPullMarkPulledRequest, db: Session = Depends(get_db), actor=Depends(require_permission("stability_pull.execute"))):
    return pulls.mark_pulled(db, actor, study_id, pull_id, payload.version, payload.pulled_at, payload.notes, notes_supplied="notes" in payload.model_fields_set)

@router.post("/{study_id}/pulls/{pull_id}/create-sample", response_model=StabilityPullResponse, status_code=201)
def create_stability_pull_sample(study_id: UUID, pull_id: UUID, payload: StabilityPullCreateSampleRequest, db: Session = Depends(get_db), actor=Depends(require_permission("stability_pull.execute"))):
    return pulls.create_sample(db, actor, study_id, pull_id, payload.version, payload.sample_number)

@router.post("/{study_id}/pulls/{pull_id}/cancel", response_model=StabilityPullResponse)
def cancel_stability_pull(study_id: UUID, pull_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("stability_pull.execute"))):
    return pulls.cancel(db, actor, study_id, pull_id, payload.version)
