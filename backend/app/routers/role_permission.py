from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.database import get_db

from app.schemas.role_permission import (
    RolePermissionCreate,
    RolePermissionResponse,
)

from app.services.role_permission_service import (
    RolePermissionService,
)


router = APIRouter()

service = RolePermissionService()


@router.get(
    "/roles/{role_id}/permissions",
    response_model=list[RolePermissionResponse],
)
def get_role_permissions(
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "role.view",
        ),
    ),
):
    return service.get_by_role(
        db,
        role_id,
    )


@router.post(
    "/roles/{role_id}/permissions",
    response_model=RolePermissionResponse,
)
def assign_permission(
    role_id: UUID,
    data: RolePermissionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "role.update",
        ),
    ),
):
    return service.assign_permission(
        db,
        role_id,
        data,
    )


@router.delete(
    "/roles/{role_id}/permissions/{permission_id}",
)
def remove_permission(
    role_id: UUID,
    permission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "role.update",
        ),
    ),
):
    return service.remove_permission(
        db,
        role_id,
        permission_id,
    )