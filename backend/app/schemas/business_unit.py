from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BusinessUnitCreate(BaseModel):
    organization_id: UUID
    business_unit_code: str
    business_unit_name: str
    description: str | None = None


class BusinessUnitUpdate(BaseModel):
    business_unit_name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class BusinessUnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    business_unit_code: str
    business_unit_name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime