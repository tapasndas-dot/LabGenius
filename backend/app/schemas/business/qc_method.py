from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.business.qc_method import MethodParameterValueType, MethodVersionStatus
from .shared import StrictSchema


class TestCreate(StrictSchema):
    test_code: str = Field(min_length=1, max_length=50)
    test_name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    test_category: str | None = Field(default=None, max_length=100)
    default_unit: str | None = Field(default=None, max_length=50)


class TestUpdate(StrictSchema):
    version: int = Field(ge=1)
    test_code: str | None = Field(default=None, min_length=1, max_length=50)
    test_name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    test_category: str | None = Field(default=None, max_length=100)
    default_unit: str | None = Field(default=None, max_length=50)


class TestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    test_code: str
    test_name: str
    description: str | None
    test_category: str | None
    default_unit: str | None
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class MethodCreate(StrictSchema):
    method_code: str = Field(min_length=1, max_length=50)
    method_name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class MethodUpdate(StrictSchema):
    version: int = Field(ge=1)
    method_code: str | None = Field(default=None, min_length=1, max_length=50)
    method_name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class MethodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    method_code: str
    method_name: str
    description: str | None
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class MethodVersionCreate(StrictSchema):
    version_number: int = Field(gt=0)
    version_label: str | None = Field(default=None, max_length=100)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    source_reference: str | None = Field(default=None, max_length=500)
    description: str | None = None


class MethodVersionUpdate(StrictSchema):
    version: int = Field(ge=1)
    version_label: str | None = Field(default=None, max_length=100)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    source_reference: str | None = Field(default=None, max_length=500)
    description: str | None = None


class MethodVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    method_id: UUID
    version_number: int
    version_label: str | None
    status: MethodVersionStatus
    effective_from: datetime | None
    effective_to: datetime | None
    source_reference: str | None
    description: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class MethodParameterCreate(StrictSchema):
    parameter_code: str = Field(min_length=1, max_length=50)
    parameter_name: str = Field(min_length=1, max_length=200)
    value_type: MethodParameterValueType
    unit: str | None = Field(default=None, max_length=50)
    default_value: str | None = None
    sequence_number: int | None = Field(default=None, gt=0)
    is_required: bool = False
    description: str | None = None


class MethodParameterUpdate(StrictSchema):
    version: int = Field(ge=1)
    parameter_code: str | None = Field(default=None, min_length=1, max_length=50)
    parameter_name: str | None = Field(default=None, min_length=1, max_length=200)
    value_type: MethodParameterValueType | None = None
    unit: str | None = Field(default=None, max_length=50)
    default_value: str | None = None
    sequence_number: int | None = Field(default=None, gt=0)
    is_required: bool | None = None
    description: str | None = None


class MethodParameterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    method_version_id: UUID
    parameter_code: str
    parameter_name: str
    value_type: MethodParameterValueType
    unit: str | None
    default_value: str | None
    sequence_number: int | None
    is_required: bool
    description: str | None
    version: int
    created_at: datetime
    updated_at: datetime
