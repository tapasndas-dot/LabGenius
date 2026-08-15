from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RoleResponse(BaseModel):
    """
    Role returned by the API.
    """

    id: UUID
    role_code: str
    role_name: str
    description: str | None
    is_active: bool
    version: int

    model_config = ConfigDict(
        from_attributes=True,
    )


class RoleCreate(BaseModel):
    """
    Request to create a role.
    """

    role_code: str
    role_name: str
    description: str | None = None


class RoleUpdate(BaseModel):
    """
    Request to update a role.
    """

    role_name: str | None = None
    description: str | None = None


class RoleStatusUpdate(BaseModel):
    """
    Request to activate or deactivate a role.
    """

    is_active: bool