"""Read-only QC operational dashboard endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import (ensure_password_change_complete,
                                   get_current_user, get_effective_permission_codes,
                                   require_permission)
from app.dependencies.database import get_db
from app.models.business.sample import SampleStatus, SampleTestStatus
from app.schemas.business.qc_dashboard import (QCDashboardSummary,
                                               QCRecentActivityRow,
                                               QCReviewQueueRow,
                                               QCWorkQueueRow)
from app.services.business.qc_dashboard_service import qc_dashboard_service

router = APIRouter()


def require_result_workflow_permission(actor=Depends(get_current_user)):
    ensure_password_change_complete(actor)
    permissions = set(get_effective_permission_codes(actor))
    if not permissions.intersection({
        "sample_test_result.review", "sample_test_result.finalize"
    }):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Result workflow permission is required.")
    return actor


@router.get("/summary", response_model=QCDashboardSummary)
def summary(db: Session = Depends(get_db),
            actor=Depends(require_permission("sample.view"))):
    return qc_dashboard_service.summary(db, actor)


@router.get("/work-queue", response_model=list[QCWorkQueueRow])
def work_queue(
    business_unit_id: UUID | None = None, division_id: UUID | None = None,
    department_id: UUID | None = None, sample_status: SampleStatus | None = None,
    sample_test_status: SampleTestStatus | None = None,
    assigned_user_id: UUID | None = None, due_from: datetime | None = None,
    due_to: datetime | None = None, db: Session = Depends(get_db),
    actor=Depends(require_permission("sample.view")),
):
    return qc_dashboard_service.work_queue(
        db, actor, business_unit_id=business_unit_id, division_id=division_id,
        department_id=department_id, sample_status=sample_status,
        sample_test_status=sample_test_status, assigned_user_id=assigned_user_id,
        due_from=due_from, due_to=due_to,
    )


@router.get("/review-queue", response_model=list[QCReviewQueueRow])
def review_queue(db: Session = Depends(get_db),
                 actor=Depends(require_result_workflow_permission)):
    return qc_dashboard_service.review_queue(db, actor)


@router.get("/recent-activity", response_model=list[QCRecentActivityRow])
def recent_activity(limit: int = Query(20, ge=1, le=100),
                    db: Session = Depends(get_db),
                    actor=Depends(require_permission("sample.view"))):
    return qc_dashboard_service.recent_activity(db, actor, limit)
