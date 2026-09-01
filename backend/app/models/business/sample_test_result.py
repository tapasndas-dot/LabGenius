from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseModel
from app.database.mixins import TimestampMixin, UUIDMixin, VersionMixin


class SampleTestResultStatus(StrEnum):
    """Result lifecycle states as defined in Blueprint."""
    DRAFT = "DRAFT"
    ENTERED = "ENTERED"
    REVIEWED = "REVIEWED"
    FINALIZED = "FINALIZED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ParameterValueType(StrEnum):
    """Supported parameter value types - mirrors MethodParameterValueType."""
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    INTEGER = "INTEGER"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    DATETIME = "DATETIME"


class SampleTestResult(UUIDMixin, TimestampMixin, VersionMixin, BaseModel):
    """
    Result/execution header for a SampleTest.

    Each SampleTest may have multiple result records for retained revision history.
    Sprint 21A does not define which revision is effective for later decisions.

    Result scope inherits through SampleTest -> Sample.
    """

    __tablename__ = "sample_test_results"
    __table_args__ = (
        UniqueConstraint("sample_test_id", "sequence_number", name="uq_sample_test_results_test_sequence"),
        CheckConstraint("status IN ('DRAFT', 'ENTERED', 'REVIEWED', 'FINALIZED', 'REJECTED', 'CANCELLED')", name="ck_sample_test_results_status"),
        CheckConstraint("sequence_number > 0", name="ck_sample_test_results_sequence_positive"),
        CheckConstraint("version > 0", name="ck_sample_test_results_version_positive"),
        CheckConstraint("completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at", name="ck_sample_test_results_timing"),
        Index("ix_sample_test_results_sample_test_status", "sample_test_id", "status"),
        Index("ix_sample_test_results_effective", "sample_test_id", "sequence_number"),
    )

    sample_test_id: Mapped[UUID] = mapped_column(ForeignKey("sample_tests.id", ondelete="RESTRICT"), nullable=False)

    # Result lifecycle: one-based sequence of revisions for this SampleTest
    sequence_number: Mapped[int] = mapped_column(nullable=False)

    # Execution timeline
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=SampleTestResultStatus.DRAFT, server_default=text("'DRAFT'"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Entry/submission
    entered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entered_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)

    # Review
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)

    # Finalization
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)

    # Notes/comments
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    sample_test = relationship("SampleTest")
    entered_by_user = relationship("User", foreign_keys=[entered_by_user_id])
    reviewed_by_user = relationship("User", foreign_keys=[reviewed_by_user_id])
    finalized_by_user = relationship("User", foreign_keys=[finalized_by_user_id])

    parameter_results = relationship("ParameterResult", back_populates="sample_test_result", passive_deletes=True)
    instrument_usages = relationship("ResultInstrumentUsage", back_populates="sample_test_result", passive_deletes=True)


class ParameterResult(UUIDMixin, TimestampMixin, VersionMixin, BaseModel):
    """
    Result value for a MethodParameter within a SampleTestResult.

    Captures the exact historical MethodParameter and its recorded value.
    Supports all MethodParameterValueType types with type-safe storage.
    """

    __tablename__ = "qc_parameter_results"
    __table_args__ = (
        UniqueConstraint("sample_test_result_id", "method_parameter_id", name="uq_parameter_results_result_parameter"),
        CheckConstraint("value_type IN ('TEXT', 'NUMBER', 'INTEGER', 'BOOLEAN', 'DATE', 'DATETIME')", name="ck_parameter_results_value_type"),
        CheckConstraint("version > 0", name="ck_parameter_results_version_positive"),
        Index("ix_parameter_results_result", "sample_test_result_id"),
        Index("ix_parameter_results_parameter", "method_parameter_id"),
    )

    sample_test_result_id: Mapped[UUID] = mapped_column(ForeignKey("sample_test_results.id", ondelete="RESTRICT"), nullable=False)
    method_parameter_id: Mapped[UUID] = mapped_column(ForeignKey("method_parameters.id", ondelete="RESTRICT"), nullable=False)

    # Value type and storage
    value_type: Mapped[str] = mapped_column(String(20), nullable=False)
    text_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    numeric_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    integer_value: Mapped[int | None] = mapped_column(nullable=True)
    boolean_value: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    date_value: Mapped[date | None] = mapped_column(Date(), nullable=True)
    datetime_value: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    sample_test_result = relationship("SampleTestResult", back_populates="parameter_results")
    method_parameter = relationship("MethodParameter")


class ResultInstrumentUsage(UUIDMixin, TimestampMixin, VersionMixin, BaseModel):
    """
    Historical record of instrument usage during a SampleTestResult execution.

    Preserves the exact Instrument used for this execution.
    Later instrument status/location/responsibility changes do not affect this record.
    """

    __tablename__ = "qc_result_instrument_usages"
    __table_args__ = (
        UniqueConstraint("sample_test_result_id", "instrument_id", name="uq_result_instrument_usages_result_instrument"),
        CheckConstraint("version > 0", name="ck_result_instrument_usages_version_positive"),
        Index("ix_result_instrument_usages_result", "sample_test_result_id"),
        Index("ix_result_instrument_usages_instrument", "instrument_id"),
    )

    sample_test_result_id: Mapped[UUID] = mapped_column(ForeignKey("sample_test_results.id", ondelete="RESTRICT"), nullable=False)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False)

    # Optional usage context
    usage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    sample_test_result = relationship("SampleTestResult", back_populates="instrument_usages")
    instrument = relationship("Instrument")
