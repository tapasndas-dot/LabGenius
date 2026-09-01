from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .shared import StrictSchema

ValueType = Literal["TEXT", "NUMBER", "INTEGER", "BOOLEAN", "DATE", "DATETIME"]


class ResultCreate(StrictSchema):
    notes: str | None = Field(default=None, max_length=5000)


class ResultUpdate(StrictSchema):
    version: int = Field(ge=1)
    notes: str | None = Field(default=None, max_length=5000)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TypedParameterValue(StrictSchema):
    value_type: ValueType
    text_value: str | None = None
    numeric_value: Decimal | None = None
    integer_value: int | None = None
    boolean_value: bool | None = None
    date_value: date | None = None
    datetime_value: datetime | None = None

    @model_validator(mode="after")
    def exactly_one_typed_value(self):
        names = ("text_value", "numeric_value", "integer_value", "boolean_value",
                 "date_value", "datetime_value")
        populated = [name for name in names if getattr(self, name) is not None]
        expected = {
            "TEXT": "text_value", "NUMBER": "numeric_value",
            "INTEGER": "integer_value", "BOOLEAN": "boolean_value",
            "DATE": "date_value", "DATETIME": "datetime_value",
        }[self.value_type]
        if populated != [expected]:
            raise ValueError(f"{self.value_type} requires exactly one {expected} value")
        if self.value_type == "TEXT" and not self.text_value.strip():
            raise ValueError("TEXT value must not be empty")
        if self.value_type == "DATETIME" and (
            self.datetime_value.tzinfo is None or self.datetime_value.utcoffset() is None
        ):
            raise ValueError("DATETIME value must include a timezone")
        return self

    def typed_values(self) -> dict:
        return self.model_dump(
            exclude={"value_type", "version", "method_parameter_id"},
            exclude_none=True,
        )


class ParameterResultCreate(TypedParameterValue):
    method_parameter_id: UUID


class ParameterResultUpdate(TypedParameterValue):
    version: int = Field(ge=1)


class InstrumentUsageCreate(StrictSchema):
    instrument_id: UUID
    usage_notes: str | None = Field(default=None, max_length=5000)


class ContextReference(BaseModel):
    id: UUID
    code: str
    name: str


class MethodVersionContext(BaseModel):
    id: UUID
    method_id: UUID
    code: str
    name: str
    version_number: int


class MethodParameterContext(BaseModel):
    id: UUID
    code: str
    name: str
    value_type: str
    unit: str | None
    is_required: bool
    sequence_number: int | None


class ParameterResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    method_parameter_id: UUID
    parameter: MethodParameterContext
    value_type: str
    text_value: str | None
    numeric_value: Decimal | None
    integer_value: int | None
    boolean_value: bool | None
    date_value: date | None
    datetime_value: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime


class InstrumentContext(BaseModel):
    id: UUID
    code: str
    name: str
    model_number: str | None
    serial_number: str | None


class InstrumentUsageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    instrument_id: UUID
    instrument: InstrumentContext
    usage_notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class ActorContext(BaseModel):
    id: UUID
    display_name: str


class ResultResponse(BaseModel):
    id: UUID
    sample_test_id: UUID
    sequence_number: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    entered_at: datetime | None
    entered_by: ActorContext | None
    notes: str | None
    sample: ContextReference
    sample_test: ContextReference
    test: ContextReference
    method_version: MethodVersionContext
    method_parameters: list[MethodParameterContext]
    parameters: list[ParameterResultResponse]
    instrument_usages: list[InstrumentUsageResponse]
    version: int
    created_at: datetime
    updated_at: datetime
