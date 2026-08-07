from sqlalchemy.orm import Session

from fastapi import HTTPException, status

from app.auth.hashing import verify_password
from app.models.user.user import User
from app.repositories.user.user_repository import UserRepository


class AuthService:

    def __init__(self):
        self.user_repository = UserRepository()

    def authenticate_user(
        self,
        db: Session,
        username: str,
        password: str,
    ) -> User:

        user = self.user_repository.get_by_username(
            db,
            username,
        )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        if not verify_password(
            password,
            user.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        return user