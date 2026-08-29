from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.auth_service import AuthService
from app.auth.dependencies import (
    get_current_user,
    get_effective_permission_codes,
    require_permission,
    require_role,
)
from app.auth.jwt import create_access_token
from app.dependencies.database import get_db
from app.models.user.user import User
from app.schemas.auth import (
    PasswordChangeRequest,
    PasswordOperationResponse,
    TokenResponse,
    CurrentUserResponse,
)
from app.services.user.password_service import PasswordService


router = APIRouter()

service = AuthService()
password_service = PasswordService()


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = service.authenticate_user(
        db,
        form_data.username,
        form_data.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    token = create_access_token(
        str(user.id),
    )

    return TokenResponse(
        access_token=token,
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
)
def get_me(
    current_user: User = Depends(
        get_current_user,
    ),
):
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "display_name": current_user.display_name,
        "force_password_change": current_user.force_password_change,
        "permissions": get_effective_permission_codes(current_user),
    }


@router.get(
    "/admin-test",
)
def admin_test(
    current_user: User = Depends(
        require_role("ADMIN"),
    ),
):
    return {
        "message": "Welcome Administrator",
        "user": current_user.username,
    }


@router.get(
    "/permission-test",
)
def permission_test(
    current_user: User = Depends(
        require_permission(
            "organization.create",
        ),
    ),
):
    return {
        "message": "Permission granted.",
        "permission": "organization.create",
        "user": current_user.username,
    }


@router.post(
    "/change-password",
    response_model=PasswordOperationResponse,
)
def change_password(
    request: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    password_service.change_password(
        db,
        current_user,
        current_password=request.current_password,
        new_password=request.new_password,
        confirm_new_password=request.confirm_new_password,
    )
    return PasswordOperationResponse(message="Password changed successfully.")
