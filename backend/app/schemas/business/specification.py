from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.business.specification import SpecificationCriterionType, SpecificationVersionStatus
from .shared import StrictSchema


class SpecificationCreate(StrictSchema):
    material_id: UUID
    specification_code: str = Field(min_length=1, max_length=50)
    specification_name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class SpecificationUpdate(StrictSchema):
    version: int = Field(ge=1)
    material_id: UUID | None = None
    specification_code: str | None = Field(default=None, min_length=1, max_length=50)
    specification_name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class SpecificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    material_id: UUID
    specification_code: str
    specification_name: str
    description: str | None
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class SpecificationVersionCreate(StrictSchema):
    version_number: int = Field(gt=0)
    version_label: str | None = Field(default=None, max_length=100)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    description: str | None = None


class SpecificationVersionUpdate(StrictSchema):
    version: int = Field(ge=1)
    version_label: str | None = Field(default=None, max_length=100)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    description: str | None = None


class SpecificationVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    specification_id: UUID
    version_number: int
    version_label: str | None
    status: SpecificationVersionStatus
    effective_from: datetime | None
    effective_to: datetime | None
    description: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class SpecificationTestCreate(StrictSchema):
    test_id: UUID
    method_version_id: UUID | None = None
    sequence_number: int = Field(gt=0)
    is_required: bool = True
    display_name: str | None = Field(default=None, max_length=200)
    instructions: str | None = None


class SpecificationTestUpdate(StrictSchema):
    version: int = Field(ge=1)
    test_id: UUID | None = None
    method_version_id: UUID | None = None
    sequence_number: int | None = Field(default=None, gt=0)
    is_required: bool | None = None
    display_name: str | None = Field(default=None, max_length=200)
    instructions: str | None = None


class SpecificationTestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    specification_version_id: UUID
    test_id: UUID
    method_version_id: UUID | None
    sequence_number: int
    is_required: bool
    display_name: str | None
    instructions: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class SpecificationLimitCreate(StrictSchema):
    parameter_name: str | None = Field(default=None, max_length=200)
    criterion_type: SpecificationCriterionType
    lower_limit: Decimal | None = None
    upper_limit: Decimal | None = None
    target_value: Decimal | None = None
    text_value: str | None = None
    boolean_value: bool | None = None
    unit: str | None = Field(default=None, max_length=50)
    sequence_number: int | None = Field(default=None, gt=0)
    description: str | None = None


class SpecificationLimitUpdate(SpecificationLimitCreate):
    version: int = Field(ge=1)
    criterion_type: SpecificationCriterionType | None = None


class SpecificationLimitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    specification_test_id: UUID
    parameter_name: str | None
    criterion_type: SpecificationCriterionType
    lower_limit: Decimal | None
    upper_limit: Decimal | None
    target_value: Decimal | None
    text_value: str | None
    boolean_value: bool | None
    unit: str | None
    sequence_number: int | None
    description: str | None
    version: int
    created_at: datetime
    updated_at: datetime
