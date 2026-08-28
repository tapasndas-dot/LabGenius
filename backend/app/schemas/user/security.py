from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserSecurityResponse(BaseModel):
    """
    Security state returned for a user.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    username: str
    account_status: str
    is_active: bool
    failed_login_attempts: int
    locked_until: datetime | None
    last_login: datetime | None
    password_changed_at: datetime | None
    force_password_change: bool


class AccountStatusUpdate(BaseModel):
    """
    Request to activate or deactivate a user account.
    """

    is_active: bool


class AccountUnlockResponse(BaseModel):
    """
    Response returned after unlocking a user account.
    """

    id: UUID
    username: str
    account_status: str
    is_active: bool
    failed_login_attempts: int
    locked_until: datetime | None