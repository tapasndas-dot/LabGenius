from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DepartmentCreate(BaseModel):
    division_id: UUID
    department_code: str
    department_name: str
    description: str | None = None


class DepartmentUpdate(BaseModel):
    department_name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    division_id: UUID
    department_code: str
    department_name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime