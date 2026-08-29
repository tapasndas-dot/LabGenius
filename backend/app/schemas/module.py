from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class ModuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; code: str; name: str; description: str | None; capability_class: str
    is_core: bool; is_active: bool; version: int; created_at: datetime; updated_at: datetime

class ModuleStateResponse(BaseModel):
    module: ModuleResponse
    is_enabled: bool
    version: int
    dependencies: list[str]

class ModuleVersionRequest(BaseModel):
    version: int | None = Field(default=None, ge=0)
