from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    occurred_at: datetime
    actor_user_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    organization_id: UUID | None
    business_unit_id: UUID | None
    division_id: UUID | None
    department_id: UUID | None
    request_id: UUID | None
    source_ip: str | None
    changes: dict[str, Any] | None
    reason: str | None
    source: str
