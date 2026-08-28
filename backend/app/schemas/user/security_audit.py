from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LoginHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    username_attempted: str
    success: bool
    event_timestamp: datetime
    failure_reason: str | None
    ip_address: str | None
    user_agent: str | None


class SecurityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_user_id: UUID | None
    target_user_id: UUID | None
    event_type: str
    event_timestamp: datetime
    details: dict[str, Any] | None
