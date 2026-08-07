from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt

from app.auth.jwt import decode_access_token
from app.dependencies.database import get_db
from app.models.user.user import User
from app.repositories.user.user_repository import UserRepository


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
)

user_repository = UserRepository()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Returns the currently authenticated user.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )

    try:
        payload = decode_access_token(token)

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        user = user_repository.get_with_roles(
            db,
            UUID(user_id),
        )

        if user is None:
            raise credentials_exception

        return user

    except jwt.PyJWTError:
        raise credentials_exception
def require_role(
    role_code: str,
    ):
        """
        Require the authenticated user
        to have a specific role.
        """

        def role_checker(
            current_user: User = Depends(
                get_current_user,
            ),
        ):

            for user_role in current_user.user_roles:

                if (
                    user_role.role.role_code
                    == role_code
                ):
                    return current_user

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{role_code}' is required."
                ),
            )

        return role_checker   