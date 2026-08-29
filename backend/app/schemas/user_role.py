from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserRoleCreate(BaseModel):
    """
    Request to assign a role to a user.
    """

    role_id: UUID
    access_scope: str = "SELF"


class UserRoleResponse(BaseModel):
    """
    User-Role assignment returned by the API.
    """

    id: UUID
    user_id: UUID
    role_id: UUID
    access_scope: str
    is_active: bool
    version: int

    model_config = ConfigDict(
        from_attributes=True,
    )
