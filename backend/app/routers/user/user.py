from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.schemas.user.user import (
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.user.user_service import UserService


router = APIRouter()

service = UserService()


@router.get(
    "/",
    response_model=list[UserResponse],
)
def get_users(
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "user.view",
        ),
    ),
):
    return service.get_all(db)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "user.view",
        ),
    ),
):
    return service.get(
        db,
        user_id,
    )


@router.post(
    "/",
    response_model=UserResponse,
)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "user.create",
        ),
    ),
):
    return service.create(
        db,
        user,
    )


@router.put(
    "/{user_id}",
    response_model=UserResponse,
)
def update_user(
    user_id: UUID,
    update: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "user.update",
        ),
    ),
):
    db_object = service.get(
        db,
        user_id,
    )

    return service.update(
        db,
        db_object,
        update,
    )


@router.delete(
    "/{user_id}",
)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "user.delete",
        ),
    ),
):
    db_object = service.get(
        db,
        user_id,
    )

    service.delete(
        db,
        db_object,
        actor_user_id=current_user.id,
    )

    return {
        "message": "User deleted successfully"
    }
