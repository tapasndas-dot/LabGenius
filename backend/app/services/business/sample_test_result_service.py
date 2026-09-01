"""Domain foundation for SampleTest result capture and frozen references."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (ResourceNotFoundException, ValidationException,
                                 VersionConflictException)
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
                            sample_test_id: UUID,
                            notes: str | None = None) -> SampleTestResult:
        sample, sample_test = self._owned_sample_test(db, organization_id, sample_test_id)
        if sample.status in ("CANCELLED", "FINALIZED"):
            raise ValidationException("The parent Sample cannot accept result capture.")
        if sample_test.status in ("CANCELLED", "FINALIZED"):
            raise ValidationException("The SampleTest cannot accept result capture.")
        self._method_version(db, sample_test)
        return self.result_repository.create(
            db, sample_test_id, self.result_repository.get_next_sequence(db, sample_test_id),
            notes=notes,
        )

    def update_draft_result(self, db: Session, result: SampleTestResult,
                            expected_version: int, values: dict) -> SampleTestResult:
        self._require_draft(result)
        started_at = values.get("started_at", result.started_at)
        completed_at = values.get("completed_at", result.completed_at)
        if started_at is not None and completed_at is not None and completed_at < started_at:
            raise ValidationException("Result completion cannot precede its start.")
        updated = self.result_repository.update_expected(
            db, result.id, expected_version, values
        )
        if updated is None:
            raise VersionConflictException("Result changed concurrently. Refresh and try again.")
        return updated

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

    def update_parameter_result(self, db: Session, result: SampleTestResult,
                                parameter_result: ParameterResult,
                                expected_version: int, value_type: str,
                                **typed_values) -> ParameterResult:
        self._require_draft(result)
        if parameter_result.sample_test_result_id != result.id:
            raise ResourceNotFoundException("ParameterResult not found.")
        parameter = db.get(MethodParameter, parameter_result.method_parameter_id)
        if parameter is None or parameter.value_type != value_type:
            raise ValidationException("MethodParameter value type does not match the result value type.")
        values = {column: None for column in self.VALUE_COLUMNS.values()}
        values.update(self._validated_values(value_type, typed_values))
        values["value_type"] = value_type
        updated = self.parameter_repository.update_expected(
            db, parameter_result.id, expected_version, values
        )
        if updated is None:
            raise VersionConflictException("Parameter result changed concurrently. Refresh and try again.")
        return updated

    def remove_parameter_result(self, db: Session, result: SampleTestResult,
                                parameter_result: ParameterResult,
                                expected_version: int) -> None:
        self._require_draft(result)
        if parameter_result.sample_test_result_id != result.id:
            raise ResourceNotFoundException("ParameterResult not found.")
        if not self.parameter_repository.delete_expected(
            db, parameter_result.id, expected_version
        ):
            raise VersionConflictException("Parameter result changed concurrently. Refresh and try again.")

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

    def remove_instrument_usage(self, db: Session, result: SampleTestResult,
                                usage: ResultInstrumentUsage,
                                expected_version: int) -> None:
        self._require_draft(result)
        if usage.sample_test_result_id != result.id:
            raise ResourceNotFoundException("Instrument usage not found.")
        if not self.instrument_usage_repository.delete_expected(
            db, usage.id, expected_version
        ):
            raise VersionConflictException("Instrument usage changed concurrently. Refresh and try again.")

    def submit(self, db: Session, organization_id: UUID, result: SampleTestResult,
               actor_id: UUID, expected_version: int) -> SampleTestResult:
        self._require_draft(result)
        sample, sample_test = self._owned_sample_test(
            db, organization_id, result.sample_test_id,
        )
        if sample.status in ("CANCELLED", "FINALIZED") or sample_test.status in ("CANCELLED", "FINALIZED"):
            raise ValidationException("The operational parent cannot accept result submission.")
        method_version = self._method_version(db, sample_test)
        parameters = db.query(MethodParameter).filter(
            MethodParameter.method_version_id == method_version.id
        ).all()
        expected = {parameter.id: parameter for parameter in parameters}
        recorded = self.parameter_repository.list_for_result(db, result.id)
        seen = set()
        for value in recorded:
            parameter = expected.get(value.method_parameter_id)
            if parameter is None:
                raise ValidationException("Result contains a parameter outside the frozen Method Version.")
            if parameter.value_type != value.value_type:
                raise ValidationException("Result value type does not match the frozen MethodParameter.")
            if value.method_parameter_id in seen:
                raise ValidationException("Result contains a duplicate parameter value.")
            seen.add(value.method_parameter_id)
            typed = {column: getattr(value, column) for column in self.VALUE_COLUMNS.values()}
            self._validated_values(value.value_type, typed)
            if (parameter.is_required and value.value_type == ParameterValueType.TEXT
                    and not value.text_value.strip()):
                raise ValidationException("Required TEXT parameter results cannot be empty.")
        missing = [parameter.parameter_name for parameter in parameters
                   if parameter.is_required and parameter.id not in seen]
        if missing:
            raise ValidationException("Required parameter results are incomplete: " + ", ".join(missing))
        return self.update_draft_result(db, result, expected_version, {
            "status": SampleTestResultStatus.ENTERED,
            "entered_at": datetime.now(timezone.utc),
            "entered_by_user_id": actor_id,
        })
