from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .shared import StrictSchema

SamplePriorityValue = Literal["LOW", "NORMAL", "HIGH", "URGENT"]


class SampleCreate(StrictSchema):
    business_unit_id: UUID | None = None
    division_id: UUID | None = None
    department_id: UUID | None = None
    sample_number: str = Field(min_length=1, max_length=100)
    external_reference: str | None = Field(default=None, max_length=200)
    material_id: UUID
    specification_version_id: UUID
    sample_description: str | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    quantity_unit: str | None = Field(default=None, max_length=50)
    received_at: datetime | None = None
    sampled_at: datetime | None = None
    due_at: datetime | None = None
    priority: SamplePriorityValue = "NORMAL"
    notes: str | None = None


class SampleUpdate(StrictSchema):
    version: int = Field(ge=1)
    business_unit_id: UUID | None = None
    division_id: UUID | None = None
    department_id: UUID | None = None
    external_reference: str | None = Field(default=None, max_length=200)
    sample_description: str | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    quantity_unit: str | None = Field(default=None, max_length=50)
    received_at: datetime | None = None
    sampled_at: datetime | None = None
    due_at: datetime | None = None
    priority: SamplePriorityValue | None = None
    notes: str | None = None


class SampleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    business_unit_id: UUID | None
    division_id: UUID | None
    department_id: UUID | None
    sample_number: str
    external_reference: str | None
    material_id: UUID
    specification_version_id: UUID
    sample_description: str | None
    quantity: Decimal | None
    quantity_unit: str | None
    received_at: datetime | None
    sampled_at: datetime | None
    due_at: datetime | None
    status: str
    priority: str
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class SampleTestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sample_id: UUID
    specification_test_id: UUID
    test_id: UUID
    method_version_id: UUID | None
    sequence_number: int
    status: str
    is_required: bool
    display_name: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class SampleTestAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sample_test_id: UUID
    assigned_user_id: UUID
    assigned_by_user_id: UUID | None
    assigned_at: datetime
    unassigned_at: datetime | None
    unassigned_by_user_id: UUID | None
    is_active: bool
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class SampleTestAssignRequest(StrictSchema):
    assigned_user_id: UUID
    expected_sample_test_version: int = Field(ge=1)
    notes: str | None = Field(default=None, max_length=500)


class SampleTestReassignRequest(SampleTestAssignRequest):
    expected_assignment_version: int = Field(ge=1)


class SampleTestUnassignRequest(StrictSchema):
    expected_assignment_version: int = Field(ge=1)
    expected_sample_test_version: int = Field(ge=1)


class SampleTestAssignmentMutationResponse(BaseModel):
    sample_test: SampleTestResponse
    assignment: SampleTestAssignmentResponse | None


class SampleTestAssigneeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    display_name: str
    account_status: str
