from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.schemas.business.sample import (
    SampleCreate, SampleResponse, SampleTestAssignRequest,
    SampleTestAssigneeResponse,
    SampleTestAssignmentMutationResponse, SampleTestAssignmentResponse,
    SampleTestReassignRequest, SampleTestResponse, SampleTestUnassignRequest,
    SampleUpdate,
)
from app.schemas.business.shared import VersionRequest
from app.services.business.sample_service import sample_api_service
from app.services.business.sample_test_assignment_api_service import sample_test_assignment_api_service

router = APIRouter()


@router.get("/assignment-users", response_model=list[SampleTestAssigneeResponse])
def list_assignment_users(db: Session = Depends(get_db), actor=Depends(require_permission("sample.view"))):
    return sample_test_assignment_api_service.assignment_users(db, actor)


@router.get("", response_model=list[SampleResponse])
def list_samples(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), search: str | None = None, status: str | None = None, priority: str | None = None, material_id: UUID | None = None, business_unit_id: UUID | None = None, division_id: UUID | None = None, department_id: UUID | None = None, db: Session = Depends(get_db), actor=Depends(require_permission("sample.view"))):
    return sample_api_service.list(db, actor, "sample.view", limit=limit, offset=offset, search=search, status=status, priority=priority, material_id=material_id, business_unit_id=business_unit_id, division_id=division_id, department_id=department_id)


@router.post("", response_model=SampleResponse, status_code=201)
def create_sample(payload: SampleCreate, db: Session = Depends(get_db), actor=Depends(require_permission("sample.create"))):
    return sample_api_service.create(db, actor, "sample.create", payload.model_dump())


@router.get("/{sample_id}", response_model=SampleResponse)
def get_sample(sample_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("sample.view"))):
    return sample_api_service.get(db, actor, sample_id, "sample.view")


@router.put("/{sample_id}", response_model=SampleResponse)
def update_sample(sample_id: UUID, payload: SampleUpdate, db: Session = Depends(get_db), actor=Depends(require_permission("sample.update"))):
    return sample_api_service.update(db, actor, sample_id, payload.version, "sample.update", payload.model_dump(exclude_unset=True, exclude={"version"}))


@router.post("/{sample_id}/cancel", response_model=SampleResponse)
def cancel_sample(sample_id: UUID, payload: VersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("sample.cancel"))):
    return sample_api_service.cancel(db, actor, sample_id, payload.version, "sample.cancel")


@router.post("/{sample_id}/generate-tests", response_model=list[SampleTestResponse])
def generate_sample_tests(sample_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("sample.update"))):
    return sample_api_service.generate_tests(db, actor, sample_id, "sample.update")


@router.get("/{sample_id}/tests", response_model=list[SampleTestResponse])
def list_sample_tests(sample_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("sample.view"))):
    return sample_api_service.list_tests(db, actor, sample_id, "sample.view")


@router.get("/{sample_id}/tests/{sample_test_id}", response_model=SampleTestResponse)
def get_sample_test(sample_id: UUID, sample_test_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("sample.view"))):
    return sample_api_service.test(db, actor, sample_id, sample_test_id, "sample.view")


@router.post("/{sample_id}/tests/{sample_test_id}/assign", response_model=SampleTestAssignmentMutationResponse)
def assign_sample_test(sample_id: UUID, sample_test_id: UUID, payload: SampleTestAssignRequest, db: Session = Depends(get_db), actor=Depends(require_permission("sample.assign"))):
    return sample_test_assignment_api_service.assign(db, actor, sample_id, sample_test_id, payload.model_dump())


@router.post("/{sample_id}/tests/{sample_test_id}/reassign", response_model=SampleTestAssignmentMutationResponse)
def reassign_sample_test(sample_id: UUID, sample_test_id: UUID, payload: SampleTestReassignRequest, db: Session = Depends(get_db), actor=Depends(require_permission("sample.assign"))):
    return sample_test_assignment_api_service.reassign(db, actor, sample_id, sample_test_id, payload.model_dump())


@router.post("/{sample_id}/tests/{sample_test_id}/unassign", response_model=SampleTestAssignmentMutationResponse)
def unassign_sample_test(sample_id: UUID, sample_test_id: UUID, payload: SampleTestUnassignRequest, db: Session = Depends(get_db), actor=Depends(require_permission("sample.assign"))):
    return sample_test_assignment_api_service.unassign(db, actor, sample_id, sample_test_id, payload.model_dump())


@router.get("/{sample_id}/tests/{sample_test_id}/assignment", response_model=SampleTestAssignmentResponse)
def get_sample_test_assignment(sample_id: UUID, sample_test_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("sample.view"))):
    return sample_test_assignment_api_service.current(db, actor, sample_id, sample_test_id)


@router.get("/{sample_id}/tests/{sample_test_id}/assignment-history", response_model=list[SampleTestAssignmentResponse])
def get_sample_test_assignment_history(sample_id: UUID, sample_test_id: UUID, db: Session = Depends(get_db), actor=Depends(require_permission("sample.view"))):
    return sample_test_assignment_api_service.history(db, actor, sample_id, sample_test_id)
