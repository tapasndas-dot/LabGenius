from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DivisionCreate(BaseModel):
    business_unit_id: UUID
    division_code: str
    division_name: str
    description: str | None = None


class DivisionUpdate(BaseModel):
    division_name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class DivisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_unit_id: UUID
    division_code: str
    division_name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime