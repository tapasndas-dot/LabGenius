from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.business.stability import StabilityProtocolVersionStatus, StabilityStudyStatus
from .shared import StrictSchema


class StabilityProtocolCreate(StrictSchema):
    protocol_code: str = Field(min_length=1, max_length=50)
    protocol_name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class StabilityProtocolUpdate(StrictSchema):
    version: int = Field(ge=1)
    protocol_code: str | None = Field(default=None, min_length=1, max_length=50)
    protocol_name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class StabilityProtocolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    protocol_code: str
    protocol_name: str
    description: str | None
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class StabilityProtocolVersionCreate(StrictSchema):
    version_number: int = Field(gt=0)
    version_label: str | None = Field(default=None, max_length=100)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    description: str | None = None


class StabilityProtocolVersionUpdate(StrictSchema):
    version: int = Field(ge=1)
    version_label: str | None = Field(default=None, max_length=100)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    description: str | None = None


class StabilityProtocolVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    stability_protocol_id: UUID
    version_number: int
    version_label: str | None
    status: StabilityProtocolVersionStatus
    effective_from: datetime | None
    effective_to: datetime | None
    description: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class StabilityProtocolConditionCreate(StrictSchema):
    sequence_number: int = Field(gt=0)
    condition_code: str = Field(min_length=1, max_length=50)
    condition_name: str = Field(min_length=1, max_length=200)
    temperature_value: Decimal | None = None
    temperature_unit: str | None = Field(default=None, max_length=20)
    temperature_tolerance: Decimal | None = None
    humidity_value: Decimal | None = None
    humidity_unit: str | None = Field(default=None, max_length=20)
    humidity_tolerance: Decimal | None = None
    description: str | None = None


class StabilityProtocolConditionUpdate(StrictSchema):
    version: int = Field(ge=1)
    sequence_number: int | None = Field(default=None, gt=0)
    condition_code: str | None = Field(default=None, min_length=1, max_length=50)
    condition_name: str | None = Field(default=None, min_length=1, max_length=200)
    temperature_value: Decimal | None = None
    temperature_unit: str | None = Field(default=None, max_length=20)
    temperature_tolerance: Decimal | None = None
    humidity_value: Decimal | None = None
    humidity_unit: str | None = Field(default=None, max_length=20)
    humidity_tolerance: Decimal | None = None
    description: str | None = None


class StabilityProtocolConditionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    stability_protocol_version_id: UUID
    sequence_number: int
    condition_code: str
    condition_name: str
    temperature_value: Decimal | None
    temperature_unit: str | None
    temperature_tolerance: Decimal | None
    humidity_value: Decimal | None
    humidity_unit: str | None
    humidity_tolerance: Decimal | None
    description: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class StabilityProtocolTimepointCreate(StrictSchema):
    sequence_number: int = Field(gt=0)
    label: str = Field(min_length=1, max_length=100)
    interval_value: int | None = Field(default=None, gt=0)
    interval_unit: str | None = Field(default=None, max_length=20)
    is_initial: bool = False
    specification_version_id: UUID
    description: str | None = None


class StabilityProtocolTimepointUpdate(StrictSchema):
    version: int = Field(ge=1)
    sequence_number: int | None = Field(default=None, gt=0)
    label: str | None = Field(default=None, min_length=1, max_length=100)
    interval_value: int | None = Field(default=None, gt=0)
    interval_unit: str | None = Field(default=None, max_length=20)
    is_initial: bool | None = None
    specification_version_id: UUID | None = None
    description: str | None = None


class StabilityProtocolTimepointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    stability_protocol_condition_id: UUID
    sequence_number: int
    label: str
    interval_value: int | None
    interval_unit: str | None
    is_initial: bool
    specification_version_id: UUID
    description: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class StabilityStudyCreate(StrictSchema):
    business_unit_id: UUID | None = None
    division_id: UUID | None = None
    department_id: UUID | None = None
    study_number: str = Field(min_length=1, max_length=100)
    study_name: str = Field(min_length=1, max_length=200)
    material_id: UUID
    stability_protocol_version_id: UUID
    start_date: date | None = None
    batch_number: str | None = Field(default=None, max_length=100)
    lot_number: str | None = Field(default=None, max_length=100)
    notes: str | None = None


class StabilityStudyUpdate(StrictSchema):
    version: int = Field(ge=1)
    business_unit_id: UUID | None = None
    division_id: UUID | None = None
    department_id: UUID | None = None
    study_name: str | None = Field(default=None, min_length=1, max_length=200)
    start_date: date | None = None
    batch_number: str | None = Field(default=None, max_length=100)
    lot_number: str | None = Field(default=None, max_length=100)
    notes: str | None = None


class StabilityStudyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    business_unit_id: UUID | None
    division_id: UUID | None
    department_id: UUID | None
    study_number: str
    study_name: str
    material_id: UUID
    stability_protocol_version_id: UUID
    start_date: date | None
    status: StabilityStudyStatus
    batch_number: str | None
    lot_number: str | None
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class StabilityStudyConditionCreate(StrictSchema):
    stability_protocol_condition_id: UUID
    instrument_id: UUID
    assigned_at: datetime | None = None
    ended_at: datetime | None = None
    notes: str | None = None


class StabilityStudyConditionUpdate(StrictSchema):
    version: int = Field(ge=1)
    stability_protocol_condition_id: UUID | None = None
    instrument_id: UUID | None = None
    assigned_at: datetime | None = None
    ended_at: datetime | None = None
    notes: str | None = None


class StabilityStudyConditionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    stability_study_id: UUID
    stability_protocol_condition_id: UUID
    instrument_id: UUID
    assigned_at: datetime | None
    ended_at: datetime | None
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime
