from uuid import UUID

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str


class PasswordOperationResponse(BaseModel):
    message: str


class CurrentUserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    display_name: str
    force_password_change: bool
    permissions: list[str]
