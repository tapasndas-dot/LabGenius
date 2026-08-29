from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.database import get_db

from app.schemas.user.security import (
    UserSecurityResponse,
    AccountUnlockResponse,
    PasswordResetRequest,
)

from app.services.user.security_service import (
    SecurityService,
)
from app.schemas.auth import PasswordOperationResponse
from app.services.user.password_service import PasswordService
from app.services.organization_scope_service import OrganizationScopeService


router = APIRouter()

service = SecurityService()
password_service = PasswordService()
scope_service = OrganizationScopeService()


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
    scope_service.ensure_can_access_user(current_user, user, "user.view")

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
    scope_service.ensure_can_access_user(current_user, user, "user.update")

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
    scope_service.ensure_can_access_user(current_user, user, "user.update")

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
    scope_service.ensure_can_access_user(current_user, user, "user.update")

    return service.unlock(
        db,
        user,
        actor_user_id=current_user.id,
    )


@router.post(
    "/{user_id}/reset-password",
    response_model=PasswordOperationResponse,
)
def reset_user_password(
    user_id: UUID,
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("user.update")),
):
    target_user = service.get_user(db, user_id)
    scope_service.ensure_can_access_user(current_user, target_user, "user.update")
    password_service.reset_password(
        db,
        target_user,
        actor_user_id=current_user.id,
        new_password=request.new_password,
        confirm_new_password=request.confirm_new_password,
    )
    return PasswordOperationResponse(message="Password reset successfully.")
