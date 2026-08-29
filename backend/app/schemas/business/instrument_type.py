from pydantic import Field

from .shared import MasterResponse, StrictSchema


class InstrumentTypeCreate(StrictSchema):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class InstrumentTypeUpdate(StrictSchema):
    version: int = Field(ge=1)
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class InstrumentTypeResponse(MasterResponse):
    pass
