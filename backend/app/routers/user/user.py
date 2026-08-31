from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.schemas.user.user import (
    UserCreate,
    UserHierarchyLookups,
    UserResponse,
    UserUpdate,
)
from app.services.user.user_service import UserService


router = APIRouter()

service = UserService()


@router.get("/hierarchy-lookups/view", response_model=UserHierarchyLookups)
def get_view_hierarchy_lookups(db: Session = Depends(get_db), current_user=Depends(require_permission("user.view"))):
    return service.hierarchy_lookups(db, current_user, "user.view")


@router.get("/hierarchy-lookups/create", response_model=UserHierarchyLookups)
def get_create_hierarchy_lookups(db: Session = Depends(get_db), current_user=Depends(require_permission("user.create"))):
    return service.hierarchy_lookups(db, current_user, "user.create")


@router.get("/hierarchy-lookups/update", response_model=UserHierarchyLookups)
def get_update_hierarchy_lookups(db: Session = Depends(get_db), current_user=Depends(require_permission("user.update"))):
    return service.hierarchy_lookups(db, current_user, "user.update")


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
    return service.get_all_scoped(db, current_user)


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
    return service.get_scoped(
        db,
        user_id,
        current_user,
        "user.view",
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
        current_user,
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
    db_object = service.get_scoped(
        db,
        user_id,
        current_user,
        "user.update",
    )

    return service.update(
        db,
        db_object,
        update,
        current_user,
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
    db_object = service.get_scoped(
        db,
        user_id,
        current_user,
        "user.delete",
    )

    service.delete(
        db,
        db_object,
        actor=current_user,
    )

    return {
        "message": "User deleted successfully"
    }
