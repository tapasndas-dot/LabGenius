from uuid import UUID

from pydantic import BaseModel


class RolePermissionCreate(BaseModel):
    """
    Request to assign a permission to a role.
    """

    permission_id: UUID


class RolePermissionResponse(BaseModel):
    """
    Role-permission assignment returned by the API.
    """

    id: UUID
    role_id: UUID
    permission_id: UUID
    is_active: bool
    version: int