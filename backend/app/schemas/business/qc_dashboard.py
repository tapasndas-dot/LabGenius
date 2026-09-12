"""Strict response contracts for the read-only QC operational dashboard."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DashboardSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DashboardReference(DashboardSchema):
    id: UUID
    code: str
    name: str


class DashboardMethodVersion(DashboardReference):
    version_number: int


class DashboardAssignment(DashboardSchema):
    assignment_id: UUID
    assigned_user_id: UUID
    assigned_user_display_name: str
    assigned_at: datetime


class DashboardResult(DashboardSchema):
    result_id: UUID
    status: str
    sequence_number: int
    entered_at: datetime | None
    reviewed_at: datetime | None
    finalized_at: datetime | None


class QCDashboardSummary(DashboardSchema):
    active_samples: int
    pending_tests: int
    assigned_or_in_progress_tests: int
    awaiting_review: int
    awaiting_finalization: int
    finalized_tests: int


class QCWorkQueueRow(DashboardSchema):
    sample_id: UUID
    sample_number: str
    sample_status: str
    sample_test_id: UUID
    sample_test_status: str
    priority: str
    due_at: datetime | None
    material: DashboardReference
    test: DashboardReference
    method_version: DashboardMethodVersion | None
    active_assignment: DashboardAssignment | None
    result: DashboardResult | None


class QCReviewQueueRow(DashboardSchema):
    queue_stage: Literal["REVIEW", "FINALIZE"]
    sample_id: UUID
    sample_number: str
    sample_test_id: UUID
    sample_test_status: str
    result_id: UUID
    result_status: str
    result_version: int
    test: DashboardReference
    method_version: DashboardMethodVersion | None
    assigned_user_display_name: str | None
    entered_at: datetime | None
    entered_by_display_name: str | None
    reviewed_at: datetime | None
    reviewed_by_display_name: str | None
    due_at: datetime | None
    priority: str


class QCRecentActivityRow(DashboardSchema):
    activity_type: Literal["SUBMITTED", "REVIEWED", "FINALIZED"]
    occurred_at: datetime
    sample_id: UUID
    sample_number: str
    sample_test_id: UUID
    result_id: UUID
    test: DashboardReference
    actor_display_name: str | None
