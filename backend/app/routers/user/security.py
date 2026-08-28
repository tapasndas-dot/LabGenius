from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.database import get_db

from app.schemas.user.security import (
    UserSecurityResponse,
    AccountUnlockResponse,
)

from app.services.user.security_service import (
    SecurityService,
)


router = APIRouter()

service = SecurityService()


@router.get(
    "/{user_id}/security",
    response_model=UserSecurityResponse,
)
def get_user_security(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "user.view",
        ),
    ),
):
    user = service.get_user(
        db,
        user_id,
    )

    return user


@router.put(
    "/{user_id}/activate",
    response_model=UserSecurityResponse,
)
def activate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "user.update",
        ),
    ),
):
    user = service.get_user(
        db,
        user_id,
    )

    return service.activate(
        db,
        user,
        actor_user_id=current_user.id,
    )


@router.put(
    "/{user_id}/deactivate",
    response_model=UserSecurityResponse,
)
def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "user.update",
        ),
    ),
):
    user = service.get_user(
        db,
        user_id,
    )

    return service.deactivate(
        db,
        user,
        actor_user_id=current_user.id,
    )


@router.put(
    "/{user_id}/unlock",
    response_model=AccountUnlockResponse,
)
def unlock_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "user.update",
        ),
    ),
):
    user = service.get_user(
        db,
        user_id,
    )

    return service.unlock(
        db,
        user,
        actor_user_id=current_user.id,
    )
