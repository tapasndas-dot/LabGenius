"""
Repository layer for result domain.

Repositories provide database access with no business logic commits.
Services enforce domain rules and transactional behavior.
"""
from uuid import UUID
from sqlalchemy import delete, func, update
from sqlalchemy.orm import Session

from app.models.business.sample_test_result import (
    SampleTestResult,
    ParameterResult,
    ResultInstrumentUsage,
)


class SampleTestResultRepository:
    """
    Repository for SampleTestResult records.

    Result revisions are retained in sequence order. Sprint 21A deliberately
    does not infer an effective result from sequence number.
    """

    def query(self, db: Session):
        return db.query(SampleTestResult)

    def get(self, db: Session, result_id: UUID) -> SampleTestResult | None:
        """Get a result by ID."""
        return self.query(db).filter(SampleTestResult.id == result_id).first()

    def get_for_sample_test(
        self, db: Session, sample_test_id: UUID, result_id: UUID
    ) -> SampleTestResult | None:
        """Get a result for a specific SampleTest (scope check)."""
        return self.query(db).filter(
            SampleTestResult.sample_test_id == sample_test_id,
            SampleTestResult.id == result_id,
        ).first()

    def list_for_sample_test(
        self, db: Session, sample_test_id: UUID
    ) -> list[SampleTestResult]:
        """
        List all result records for a SampleTest in sequence order.
        Includes draft, finalized, and history records.
        """
        return self.query(db).filter(
            SampleTestResult.sample_test_id == sample_test_id
        ).order_by(
            SampleTestResult.sequence_number.desc(),
            SampleTestResult.id,
        ).all()

    def get_next_sequence(self, db: Session, sample_test_id: UUID) -> int:
        """Get the next sequence number for a new result revision."""
        max_seq = self.query(db).filter(
            SampleTestResult.sample_test_id == sample_test_id
        ).with_entities(func.max(SampleTestResult.sequence_number)).scalar() or 0
        return max_seq + 1

    def create(
        self,
        db: Session,
        sample_test_id: UUID,
        sequence_number: int,
        status: str = "DRAFT",
        notes: str | None = None,
    ) -> SampleTestResult:
        """Create a new result record."""
        record = SampleTestResult(
            sample_test_id=sample_test_id,
            sequence_number=sequence_number,
            status=status,
            notes=notes,
        )
        db.add(record)
        db.flush()
        return record

    def update_expected(
        self,
        db: Session,
        result_id: UUID,
        expected_version: int,
        values: dict,
    ) -> SampleTestResult | None:
        """
        Update a result only if version matches (optimistic concurrency).

        Returns updated record or None if version mismatch.
        Caller must not rely on row count - use returned object.
        """
        updated_id = db.execute(
            update(SampleTestResult).where(
                SampleTestResult.id == result_id,
                SampleTestResult.version == expected_version,
            ).values(
                **values,
                version=SampleTestResult.version + 1,
                updated_at=func.now(),
            ).returning(SampleTestResult.id)
        ).scalar_one_or_none()

        if updated_id is None:
            return None
        db.flush()
        return db.get(SampleTestResult, updated_id)


class ParameterResultRepository:
    """
    Repository for parameter result values.

    Each parameter result links a SampleTestResult to its exact MethodParameter
    and stores the recorded value in type-safe columns.
    """

    def query(self, db: Session):
        return db.query(ParameterResult)

    def get(self, db: Session, parameter_result_id: UUID) -> ParameterResult | None:
        """Get a parameter result by ID."""
        return self.query(db).filter(ParameterResult.id == parameter_result_id).first()

    def list_for_result(
        self, db: Session, sample_test_result_id: UUID
    ) -> list[ParameterResult]:
        """List all parameter results for a result record."""
        return self.query(db).filter(
            ParameterResult.sample_test_result_id == sample_test_result_id
        ).all()

    def get_for_result_and_parameter(
        self,
        db: Session,
        sample_test_result_id: UUID,
        method_parameter_id: UUID,
    ) -> ParameterResult | None:
        """Get or check if a specific parameter has a result value."""
        return self.query(db).filter(
            ParameterResult.sample_test_result_id == sample_test_result_id,
            ParameterResult.method_parameter_id == method_parameter_id,
        ).first()

    def create(
        self,
        db: Session,
        sample_test_result_id: UUID,
        method_parameter_id: UUID,
        value_type: str,
        **typed_values,
    ) -> ParameterResult:
        """
        Create a parameter result with type-safe value storage.

        Pass only the relevant typed_value for the value_type:
        - TEXT: text_value
        - NUMBER: numeric_value
        - INTEGER: integer_value
        - BOOLEAN: boolean_value
        - DATE: date_value
        - DATETIME: datetime_value
        """
        record = ParameterResult(
            sample_test_result_id=sample_test_result_id,
            method_parameter_id=method_parameter_id,
            value_type=value_type,
            **typed_values,
        )
        db.add(record)
        db.flush()
        return record

    def update_expected(
        self,
        db: Session,
        parameter_result_id: UUID,
        expected_version: int,
        values: dict,
    ) -> ParameterResult | None:
        """Update a parameter result only if version matches."""
        updated_id = db.execute(
            update(ParameterResult).where(
                ParameterResult.id == parameter_result_id,
                ParameterResult.version == expected_version,
            ).values(
                **values,
                version=ParameterResult.version + 1,
                updated_at=func.now(),
            ).returning(ParameterResult.id)
        ).scalar_one_or_none()

        if updated_id is None:
            return None
        db.flush()
        return db.get(ParameterResult, updated_id)

    def delete_expected(self, db: Session, parameter_result_id: UUID,
                        expected_version: int) -> bool:
        deleted_id = db.execute(
            delete(ParameterResult).where(
                ParameterResult.id == parameter_result_id,
                ParameterResult.version == expected_version,
            ).returning(ParameterResult.id)
        ).scalar_one_or_none()
        db.flush()
        return deleted_id is not None


class ResultInstrumentUsageRepository:
    """
    Repository for instrument usage records.

    Records the exact historical instrument used during a result execution.
    Later changes to the instrument (status, location, ownership) do not
    affect this historical record.
    """

    def query(self, db: Session):
        return db.query(ResultInstrumentUsage)

    def get(self, db: Session, usage_id: UUID) -> ResultInstrumentUsage | None:
        """Get an instrument usage record by ID."""
        return self.query(db).filter(ResultInstrumentUsage.id == usage_id).first()

    def list_for_result(
        self, db: Session, sample_test_result_id: UUID
    ) -> list[ResultInstrumentUsage]:
        """List all instruments used in a result execution."""
        return self.query(db).filter(
            ResultInstrumentUsage.sample_test_result_id == sample_test_result_id
        ).all()

    def get_for_result_and_instrument(
        self,
        db: Session,
        sample_test_result_id: UUID,
        instrument_id: UUID,
    ) -> ResultInstrumentUsage | None:
        """Check if an instrument is already recorded for this result."""
        return self.query(db).filter(
            ResultInstrumentUsage.sample_test_result_id == sample_test_result_id,
            ResultInstrumentUsage.instrument_id == instrument_id,
        ).first()

    def create(
        self,
        db: Session,
        sample_test_result_id: UUID,
        instrument_id: UUID,
        usage_notes: str | None = None,
    ) -> ResultInstrumentUsage:
        """Record an instrument used in this result execution."""
        record = ResultInstrumentUsage(
            sample_test_result_id=sample_test_result_id,
            instrument_id=instrument_id,
            usage_notes=usage_notes,
        )
        db.add(record)
        db.flush()
        return record

    def update_expected(
        self,
        db: Session,
        usage_id: UUID,
        expected_version: int,
        values: dict,
    ) -> ResultInstrumentUsage | None:
        """Update an instrument usage record only if version matches."""
        updated_id = db.execute(
            update(ResultInstrumentUsage).where(
                ResultInstrumentUsage.id == usage_id,
                ResultInstrumentUsage.version == expected_version,
            ).values(
                **values,
                version=ResultInstrumentUsage.version + 1,
                updated_at=func.now(),
            ).returning(ResultInstrumentUsage.id)
        ).scalar_one_or_none()

        if updated_id is None:
            return None
        db.flush()
        return db.get(ResultInstrumentUsage, updated_id)

    def delete_expected(self, db: Session, usage_id: UUID,
                        expected_version: int) -> bool:
        deleted_id = db.execute(
            delete(ResultInstrumentUsage).where(
                ResultInstrumentUsage.id == usage_id,
                ResultInstrumentUsage.version == expected_version,
            ).returning(ResultInstrumentUsage.id)
        ).scalar_one_or_none()
        db.flush()
        return deleted_id is not None
