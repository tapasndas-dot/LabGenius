from pydantic import Field

from app.models.business.material import MaterialType
from .shared import MasterResponse, StrictSchema


class MaterialCreate(StrictSchema):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    material_type: MaterialType
    description: str | None = None
    default_unit_of_measure: str | None = Field(default=None, max_length=50)


class MaterialUpdate(StrictSchema):
    version: int = Field(ge=1)
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    material_type: MaterialType | None = None
    description: str | None = None
    default_unit_of_measure: str | None = Field(default=None, max_length=50)


class MaterialResponse(MasterResponse):
    material_type: MaterialType
    default_unit_of_measure: str | None
