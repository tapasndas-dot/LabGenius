from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.schemas.user_role import (
    UserRoleCreate,
    UserRoleResponse,
)
from app.services.user_role_service import UserRoleService


router = APIRouter()

service = UserRoleService()


@router.get(
    "/users/{user_id}/roles",
    response_model=list[UserRoleResponse],
)
def get_user_roles(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "user.view",
        ),
    ),
):
    return service.get_by_user(
        db,
        user_id,
        current_user,
    )


@router.post(
    "/users/{user_id}/roles",
    response_model=UserRoleResponse,
)
def assign_user_role(
    user_id: UUID,
    data: UserRoleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "user.update",
        ),
    ),
):
    return service.assign_role(
        db,
        user_id,
        data,
        current_user,
    )


@router.delete(
    "/users/{user_id}/roles/{role_id}",
)
def remove_user_role(
    user_id: UUID,
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "user.update",
        ),
    ),
):
    return service.remove_role(
        db,
        user_id,
        role_id,
        current_user,
    )
