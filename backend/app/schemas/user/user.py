from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    organization_id: UUID
    business_unit_id: UUID
    division_id: UUID
    department_id: UUID
    designation_id: UUID

    employee_code: str

    first_name: str
    last_name: str
    display_name: str

    email: str
    mobile: str | None = None

    username: str
    password: str

    timezone: str = "Asia/Kolkata"
    language: str = "en"


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None

    email: str | None = None
    mobile: str | None = None

    organization_id: UUID | None = None
    business_unit_id: UUID | None = None
    division_id: UUID | None = None
    department_id: UUID | None = None
    designation_id: UUID | None = None

    timezone: str | None = None
    language: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    organization_id: UUID
    business_unit_id: UUID
    division_id: UUID
    department_id: UUID
    designation_id: UUID

    employee_code: str

    first_name: str
    last_name: str
    display_name: str

    email: str
    mobile: str | None

    username: str

    account_status: str

    timezone: str
    language: str

    failed_login_attempts: int

    last_login: datetime | None

    created_at: datetime
    updated_at: datetime


class UserHierarchyOrganization(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_code: str
    organization_name: str


class UserHierarchyBusinessUnit(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    business_unit_code: str
    business_unit_name: str


class UserHierarchyDivision(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    business_unit_id: UUID
    division_code: str
    division_name: str


class UserHierarchyDepartment(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    division_id: UUID
    department_code: str
    department_name: str


class UserHierarchyDesignation(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    department_id: UUID
    designation_code: str
    designation_name: str


class UserHierarchyLookups(BaseModel):
    organizations: list[UserHierarchyOrganization]
    business_units: list[UserHierarchyBusinessUnit]
    divisions: list[UserHierarchyDivision]
    departments: list[UserHierarchyDepartment]
    designations: list[UserHierarchyDesignation]
