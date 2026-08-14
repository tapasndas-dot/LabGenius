from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PermissionResponse(BaseModel):
    """
    Permission returned by the API.
    """

    id: UUID
    permission_code: str
    permission_name: str
    description: str | None
    is_active: bool
    version: int

    model_config = ConfigDict(
        from_attributes=True,
    )


class PermissionStatusUpdate(BaseModel):
    """
    Request to activate or deactivate a permission.
    """

    is_active: bool