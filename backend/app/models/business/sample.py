from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseModel
from app.database.mixins import TimestampMixin, UUIDMixin, VersionMixin


class SampleStatus(StrEnum):
    REGISTERED = "REGISTERED"
    IN_TESTING = "IN_TESTING"
    REVIEW = "REVIEW"
    FINALIZED = "FINALIZED"
    CANCELLED = "CANCELLED"


class SamplePriority(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class SampleTestStatus(StrEnum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESULT_ENTERED = "RESULT_ENTERED"
    REVIEWED = "REVIEWED"
    FINALIZED = "FINALIZED"
    CANCELLED = "CANCELLED"


class Sample(UUIDMixin, TimestampMixin, VersionMixin, BaseModel):
    __tablename__ = "qc_samples"
    __table_args__ = (
        UniqueConstraint("organization_id", "sample_number", name="uq_qc_samples_organization_number"),
        CheckConstraint("status IN ('REGISTERED', 'IN_TESTING', 'REVIEW', 'FINALIZED', 'CANCELLED')", name="ck_qc_samples_status"),
        CheckConstraint("priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')", name="ck_qc_samples_priority"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_qc_samples_quantity_positive"),
        CheckConstraint("version > 0", name="ck_qc_samples_version_positive"),
        Index("ix_qc_samples_organization_status", "organization_id", "status"),
        Index("ix_qc_samples_hierarchy", "organization_id", "business_unit_id", "division_id", "department_id"),
    )
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    business_unit_id: Mapped[UUID | None] = mapped_column(ForeignKey("business_units.id", ondelete="RESTRICT"), nullable=True, index=True)
    division_id: Mapped[UUID | None] = mapped_column(ForeignKey("divisions.id", ondelete="RESTRICT"), nullable=True, index=True)
    department_id: Mapped[UUID | None] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=True, index=True)
    sample_number: Mapped[str] = mapped_column(String(100), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    material_id: Mapped[UUID] = mapped_column(ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False, index=True)
    specification_version_id: Mapped[UUID] = mapped_column(ForeignKey("specification_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    sample_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    quantity_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sampled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=SampleStatus.REGISTERED, server_default=text("'REGISTERED'"))
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default=SamplePriority.NORMAL, server_default=text("'NORMAL'"))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sample_tests = relationship("SampleTest", back_populates="sample", passive_deletes=True)


class SampleTest(UUIDMixin, TimestampMixin, VersionMixin, BaseModel):
    __tablename__ = "sample_tests"
    __table_args__ = (
        UniqueConstraint("sample_id", "specification_test_id", name="uq_sample_tests_sample_specification_test"),
        CheckConstraint("sequence_number > 0", name="ck_sample_tests_sequence_positive"),
        CheckConstraint("status IN ('PENDING', 'ASSIGNED', 'IN_PROGRESS', 'RESULT_ENTERED', 'REVIEWED', 'FINALIZED', 'CANCELLED')", name="ck_sample_tests_status"),
        CheckConstraint("version > 0", name="ck_sample_tests_version_positive"),
        Index("ix_sample_tests_sample_status", "sample_id", "status"),
    )
    sample_id: Mapped[UUID] = mapped_column(ForeignKey("qc_samples.id", ondelete="RESTRICT"), nullable=False, index=True)
    specification_test_id: Mapped[UUID] = mapped_column(ForeignKey("specification_tests.id", ondelete="RESTRICT"), nullable=False, index=True)
    test_id: Mapped[UUID] = mapped_column(ForeignKey("qc_tests.id", ondelete="RESTRICT"), nullable=False, index=True)
    method_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("method_versions.id", ondelete="RESTRICT"), nullable=True, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=SampleTestStatus.PENDING, server_default=text("'PENDING'"))
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sample = relationship("Sample", back_populates="sample_tests")
    specification_test = relationship("SpecificationTest")
