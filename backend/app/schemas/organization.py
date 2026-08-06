from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrganizationCreate(BaseModel):
    organization_code: str
    organization_name: str
    legal_name: str | None = None
    registration_number: str | None = None
    tax_number: str | None = None
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    timezone: str = "Asia/Kolkata"
    currency_code: str = "INR"


class OrganizationUpdate(BaseModel):
    organization_name: str | None = None
    legal_name: str | None = None
    registration_number: str | None = None
    tax_number: str | None = None
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    timezone: str | None = None
    currency_code: str | None = None
    is_active: bool | None = None


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_code: str
    organization_name: str
    legal_name: str | None
    registration_number: str | None
    tax_number: str | None
    website: str | None
    email: str | None
    phone: str | None
    timezone: str
    currency_code: str
    is_active: bool
    created_at: datetime
    updated_at: datetime