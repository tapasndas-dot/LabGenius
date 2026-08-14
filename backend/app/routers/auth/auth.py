from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.auth_service import AuthService
from app.auth.dependencies import (
    get_current_user,
    require_permission,
    require_role,
)
from app.auth.jwt import create_access_token
from app.dependencies.database import get_db
from app.models.user.user import User
from app.schemas.auth import TokenResponse


router = APIRouter()

service = AuthService()


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = service.authenticate_user(
        db,
        form_data.username,
        form_data.password,
    )

    token = create_access_token(
        str(user.id),
    )

    return TokenResponse(
        access_token=token,
    )


@router.get(
    "/me",
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