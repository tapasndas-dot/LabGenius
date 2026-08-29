from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .shared import StrictSchema


InstrumentStatusValue = Literal[
    "AVAILABLE", "IN_USE", "UNDER_CALIBRATION", "UNDER_MAINTENANCE",
    "OUT_OF_SERVICE", "QUALIFICATION_PENDING", "RETIRED",
]
InstrumentCriticalityValue = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class InstrumentFields(StrictSchema):
    business_unit_id: UUID | None = None
    division_id: UUID | None = None
    department_id: UUID | None = None
    instrument_type_id: UUID
    manufacturer_id: UUID | None = None
    location_id: UUID | None = None
    responsible_user_id: UUID | None = None
    instrument_code: str = Field(min_length=1, max_length=50)
    instrument_name: str = Field(min_length=1, max_length=200)
    model_number: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    description: str | None = None
    status: InstrumentStatusValue = "AVAILABLE"
    criticality: InstrumentCriticalityValue | None = None
    calibration_required: bool = False
    maintenance_required: bool = False
    qualification_required: bool = False


class InstrumentCreate(InstrumentFields):
    pass


class InstrumentUpdate(StrictSchema):
    version: int = Field(ge=1)
    business_unit_id: UUID | None = None
    division_id: UUID | None = None
    department_id: UUID | None = None
    instrument_type_id: UUID | None = None
    manufacturer_id: UUID | None = None
    location_id: UUID | None = None
    responsible_user_id: UUID | None = None
    instrument_code: str | None = Field(default=None, min_length=1, max_length=50)
    instrument_name: str | None = Field(default=None, min_length=1, max_length=200)
    model_number: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    description: str | None = None
    status: InstrumentStatusValue | None = None
    criticality: InstrumentCriticalityValue | None = None
    calibration_required: bool | None = None
    maintenance_required: bool | None = None
    qualification_required: bool | None = None


class InstrumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    business_unit_id: UUID | None
    division_id: UUID | None
    department_id: UUID | None
    instrument_type_id: UUID
    manufacturer_id: UUID | None
    location_id: UUID | None
    responsible_user_id: UUID | None
    instrument_code: str
    instrument_name: str
    model_number: str | None
    serial_number: str | None
    description: str | None
    status: str
    criticality: str | None
    calibration_required: bool
    maintenance_required: bool
    qualification_required: bool
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime
