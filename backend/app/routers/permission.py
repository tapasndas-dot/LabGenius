from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.schemas.permission import (
    PermissionResponse,
    PermissionStatusUpdate,
)
from app.services.permission_service import PermissionService


router = APIRouter()

service = PermissionService()


@router.get(
    "/",
    response_model=list[PermissionResponse],
)
def get_permissions(
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "permission.view",
        ),
    ),
):
    return service.get_all(db)


@router.get(
    "/active",
    response_model=list[PermissionResponse],
)
def get_active_permissions(
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "permission.view",
        ),
    ),
):
    return service.get_active(db)


@router.get(
    "/{permission_id}",
    response_model=PermissionResponse,
)
def get_permission(
    permission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "permission.view",
        ),
    ),
):
    return service.get(
        db,
        permission_id,
    )


@router.put(
    "/{permission_id}/status",
    response_model=PermissionResponse,
)
def update_permission_status(
    permission_id: UUID,
    update: PermissionStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "permission.update",
        ),
    ),
):
    return service.update_status(
        db,
        permission_id,
        update,
    )