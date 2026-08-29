from uuid import UUID

from pydantic import Field

from app.models.business.location import LocationType
from .shared import MasterResponse, StrictSchema


class LocationCreate(StrictSchema):
    parent_location_id: UUID | None = None
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    location_type: LocationType
    description: str | None = None


class LocationUpdate(StrictSchema):
    version: int = Field(ge=1)
    parent_location_id: UUID | None = None
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    location_type: LocationType | None = None
    description: str | None = None


class LocationResponse(MasterResponse):
    parent_location_id: UUID | None
    location_type: LocationType
