from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.schemas.role import (
    RoleCreate,
    RoleResponse,
    RoleStatusUpdate,
    RoleUpdate,
)
from app.services.role_service import RoleService


router = APIRouter()

service = RoleService()


@router.get(
    "/",
    response_model=list[RoleResponse],
)
def get_roles(
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "role.view",
        ),
    ),
):
    return service.get_all(db)


@router.get(
    "/active",
    response_model=list[RoleResponse],
)
def get_active_roles(
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "role.view",
        ),
    ),
):
    return service.get_active(db)


@router.get(
    "/{role_id}",
    response_model=RoleResponse,
)
def get_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "role.view",
        ),
    ),
):
    return service.get(
        db,
        role_id,
    )


@router.post(
    "/",
    response_model=RoleResponse,
)
def create_role(
    role: RoleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "role.create",
        ),
    ),
):
    return service.create(
        db,
        role,
        current_user,
    )


@router.put(
    "/{role_id}",
    response_model=RoleResponse,
)
def update_role(
    role_id: UUID,
    update: RoleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "role.update",
        ),
    ),
):
    role = service.get(
        db,
        role_id,
    )

    return service.update(
        db,
        role,
        update,
    )


@router.put(
    "/{role_id}/status",
    response_model=RoleResponse,
)
def update_role_status(
    role_id: UUID,
    update: RoleStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "role.update",
        ),
    ),
):
    return service.update_status(
        db,
        role_id,
        update,
        current_user,
        actor_user_id=current_user.id,
        actor=current_user,
    )
