"""Domain foundation for SampleTest result capture and frozen references."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.models.business.instrument import Instrument
from app.models.business.qc_method import MethodParameter, MethodVersion
from app.models.business.sample import Sample, SampleTest
from app.models.business.sample_test_result import (
    ParameterResult, ParameterValueType, ResultInstrumentUsage,
    SampleTestResult, SampleTestResultStatus,
)
from app.repositories.business.sample_repository import SampleRepository
from app.repositories.business.sample_test_result_repository import (
    ParameterResultRepository, ResultInstrumentUsageRepository,
    SampleTestResultRepository,
)


class SampleTestResultService:
    """Validate draft result content without implementing later workflow routes."""

    VALUE_COLUMNS = {
        ParameterValueType.TEXT: "text_value",
        ParameterValueType.NUMBER: "numeric_value",
        ParameterValueType.INTEGER: "integer_value",
        ParameterValueType.BOOLEAN: "boolean_value",
        ParameterValueType.DATE: "date_value",
        ParameterValueType.DATETIME: "datetime_value",
    }

    def __init__(self, result_repository=None, parameter_repository=None,
                 instrument_usage_repository=None, sample_repository=None):
        self.result_repository = result_repository or SampleTestResultRepository()
        self.parameter_repository = parameter_repository or ParameterResultRepository()
        self.instrument_usage_repository = instrument_usage_repository or ResultInstrumentUsageRepository()
        self.sample_repository = sample_repository or SampleRepository()

    def _owned_sample_test(self, db: Session, organization_id: UUID,
                           sample_test_id: UUID) -> tuple[Sample, SampleTest]:
        sample_test = db.get(SampleTest, sample_test_id)
        if sample_test is None:
            raise ResourceNotFoundException("SampleTest not found.")
        sample = self.sample_repository.get(db, organization_id, sample_test.sample_id)
        if sample is None:
            raise ResourceNotFoundException("SampleTest not found.")
        return sample, sample_test

    @staticmethod
    def _method_version(db: Session, sample_test: SampleTest) -> MethodVersion:
        version = db.get(MethodVersion, sample_test.method_version_id)
        if sample_test.method_version_id is None or version is None:
            raise ValidationException("SampleTest has no frozen Method Version basis.")
        return version

    @staticmethod
    def _require_draft(result: SampleTestResult) -> None:
        if result.status != SampleTestResultStatus.DRAFT:
            raise ValidationException("Result content is editable only while DRAFT.")

    def create_draft_result(self, db: Session, organization_id: UUID,
                            sample_test_id: UUID) -> SampleTestResult:
        sample, sample_test = self._owned_sample_test(db, organization_id, sample_test_id)
        if sample.status in ("CANCELLED", "FINALIZED"):
            raise ValidationException("The parent Sample cannot accept result capture.")
        if sample_test.status in ("CANCELLED", "FINALIZED"):
            raise ValidationException("The SampleTest cannot accept result capture.")
        self._method_version(db, sample_test)
        return self.result_repository.create(
            db, sample_test_id, self.result_repository.get_next_sequence(db, sample_test_id)
        )

    @classmethod
    def _validated_values(cls, value_type: str, typed_values: dict) -> dict:
        try:
            declared = ParameterValueType(value_type)
        except ValueError as exc:
            raise ValidationException("Unsupported parameter value type.") from exc
        unknown = set(typed_values) - set(cls.VALUE_COLUMNS.values())
        populated = {key for key, value in typed_values.items() if value is not None}
        expected = cls.VALUE_COLUMNS[declared]
        if unknown or populated != {expected}:
            raise ValidationException(f"{declared.value} requires exactly one {expected} value.")
        value = typed_values[expected]
        valid = {
            ParameterValueType.TEXT: lambda item: isinstance(item, str),
            ParameterValueType.NUMBER: lambda item: isinstance(item, Decimal) and not isinstance(item, bool),
            ParameterValueType.INTEGER: lambda item: isinstance(item, int) and not isinstance(item, bool),
            ParameterValueType.BOOLEAN: lambda item: isinstance(item, bool),
            ParameterValueType.DATE: lambda item: isinstance(item, date) and not isinstance(item, datetime),
            ParameterValueType.DATETIME: lambda item: isinstance(item, datetime) and item.tzinfo is not None and item.utcoffset() is not None,
        }
        if not valid[declared](value):
            raise ValidationException(f"Invalid Python value for {declared.value}.")
        return {expected: value}

    def add_parameter_result(self, db: Session, result_id: UUID,
                             method_parameter_id: UUID, value_type: str,
                             **typed_values) -> ParameterResult:
        result = self.result_repository.get(db, result_id)
        if result is None:
            raise ResourceNotFoundException("Result not found.")
        self._require_draft(result)
        sample_test = db.get(SampleTest, result.sample_test_id)
        if sample_test is None:
            raise ResourceNotFoundException("SampleTest not found.")
        method_version = self._method_version(db, sample_test)
        parameter = db.get(MethodParameter, method_parameter_id)
        if parameter is None:
            raise ResourceNotFoundException("MethodParameter not found.")
        if parameter.method_version_id != method_version.id:
            raise ValidationException("MethodParameter is outside the frozen Method Version.")
        if parameter.value_type != value_type:
            raise ValidationException("MethodParameter value type does not match the result value type.")
        if self.parameter_repository.get_for_result_and_parameter(db, result.id, parameter.id) is not None:
            raise ValidationException("This parameter already has a result value.")
        values = self._validated_values(value_type, typed_values)
        return self.parameter_repository.create(db, result.id, parameter.id, value_type, **values)

    def add_instrument_usage(self, db: Session, organization_id: UUID,
                             result_id: UUID, instrument_id: UUID,
                             usage_notes: str | None = None) -> ResultInstrumentUsage:
        result = self.result_repository.get(db, result_id)
        if result is None:
            raise ResourceNotFoundException("Result not found.")
        self._require_draft(result)
        self._owned_sample_test(db, organization_id, result.sample_test_id)
        instrument = db.get(Instrument, instrument_id)
        if instrument is None:
            raise ResourceNotFoundException("Instrument not found.")
        if instrument.organization_id != organization_id:
            raise ValidationException("Instrument must belong to the result organization.")
        if self.instrument_usage_repository.get_for_result_and_instrument(db, result.id, instrument.id) is not None:
            raise ValidationException("Instrument is already recorded for this result.")
        return self.instrument_usage_repository.create(db, result.id, instrument.id, usage_notes)
