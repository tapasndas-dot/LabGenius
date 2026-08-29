from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VersionRequest(StrictSchema):
    version: int = Field(ge=1)


class MasterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    code: str
    name: str
    description: str | None
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime
