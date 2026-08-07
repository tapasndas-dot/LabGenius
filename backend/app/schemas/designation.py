from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DesignationCreate(BaseModel):
    department_id: UUID
    designation_code: str
    designation_name: str
    description: str | None = None

    can_approve_workflows: bool = False
    can_manage_assets: bool = False
    can_schedule_calibration: bool = False
    can_execute_calibration: bool = False
    can_close_service: bool = False
    can_manage_documents: bool = False
    can_review_results: bool = False
    can_release_results: bool = False
    can_manage_users: bool = False
    can_view_reports: bool = False


class DesignationUpdate(BaseModel):
    designation_name: str | None = None
    description: str | None = None

    can_approve_workflows: bool | None = None
    can_manage_assets: bool | None = None
    can_schedule_calibration: bool | None = None
    can_execute_calibration: bool | None = None
    can_close_service: bool | None = None
    can_manage_documents: bool | None = None
    can_review_results: bool | None = None
    can_release_results: bool | None = None
    can_manage_users: bool | None = None
    can_view_reports: bool | None = None

    is_active: bool | None = None


class DesignationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    department_id: UUID

    designation_code: str
    designation_name: str
    description: str | None

    can_approve_workflows: bool
    can_manage_assets: bool
    can_schedule_calibration: bool
    can_execute_calibration: bool
    can_close_service: bool
    can_manage_documents: bool
    can_review_results: bool
    can_release_results: bool
    can_manage_users: bool
    can_view_reports: bool

    is_active: bool
    created_at: datetime
    updated_at: datetime