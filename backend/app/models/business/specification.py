from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseModel
from app.database.base_entities import MasterEntity
from app.database.mixins import TimestampMixin, UUIDMixin, VersionMixin


class SpecificationVersionStatus(StrEnum):
    DRAFT = "DRAFT"; APPROVED = "APPROVED"; RETIRED = "RETIRED"; SUPERSEDED = "SUPERSEDED"


class SpecificationCriterionType(StrEnum):
    BETWEEN = "BETWEEN"; MINIMUM = "MINIMUM"; MAXIMUM = "MAXIMUM"; EQUAL = "EQUAL"
    TEXT_MATCH = "TEXT_MATCH"; BOOLEAN = "BOOLEAN"; INFORMATIONAL = "INFORMATIONAL"


class Specification(MasterEntity):
    __tablename__ = "specifications"
    __table_args__ = (
        UniqueConstraint("organization_id", "specification_code", name="uq_specifications_organization_code"),
        CheckConstraint("version > 0", name="ck_specifications_version_positive"),
        Index("ix_specifications_organization_active", "organization_id", "is_active"),
    )
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    material_id: Mapped[UUID] = mapped_column(ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False, index=True)
    specification_code: Mapped[str] = mapped_column(String(50), nullable=False)
    specification_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    specification_versions = relationship("SpecificationVersion", back_populates="specification", passive_deletes=True)


class SpecificationVersion(UUIDMixin, TimestampMixin, VersionMixin, BaseModel):
    __tablename__ = "specification_versions"
    __table_args__ = (
        UniqueConstraint("specification_id", "version_number", name="uq_specification_versions_specification_number"),
        CheckConstraint("version_number > 0", name="ck_specification_versions_number_positive"),
        CheckConstraint("status IN ('DRAFT', 'APPROVED', 'RETIRED', 'SUPERSEDED')", name="ck_specification_versions_status"),
        CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_specification_versions_effectivity"),
        CheckConstraint("version > 0", name="ck_specification_versions_version_positive"),
    )
    specification_id: Mapped[UUID] = mapped_column(ForeignKey("specifications.id", ondelete="RESTRICT"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=SpecificationVersionStatus.DRAFT, server_default=text("'DRAFT'"))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    specification = relationship("Specification", back_populates="specification_versions")
    specification_tests = relationship("SpecificationTest", back_populates="specification_version", passive_deletes=True)


class SpecificationTest(UUIDMixin, TimestampMixin, VersionMixin, BaseModel):
    __tablename__ = "specification_tests"
    __table_args__ = (
        UniqueConstraint("specification_version_id", "test_id", name="uq_specification_tests_version_test"),
        UniqueConstraint("specification_version_id", "sequence_number", name="uq_specification_tests_version_sequence"),
        CheckConstraint("sequence_number > 0", name="ck_specification_tests_sequence_positive"),
        CheckConstraint("version > 0", name="ck_specification_tests_version_positive"),
    )
    specification_version_id: Mapped[UUID] = mapped_column(ForeignKey("specification_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    test_id: Mapped[UUID] = mapped_column(ForeignKey("qc_tests.id", ondelete="RESTRICT"), nullable=False, index=True)
    method_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("method_versions.id", ondelete="RESTRICT"), nullable=True, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    specification_version = relationship("SpecificationVersion", back_populates="specification_tests")
    limits = relationship("SpecificationLimit", back_populates="specification_test", passive_deletes=True)


class SpecificationLimit(UUIDMixin, TimestampMixin, VersionMixin, BaseModel):
    __tablename__ = "specification_limits"
    __table_args__ = (
        CheckConstraint("criterion_type IN ('BETWEEN', 'MINIMUM', 'MAXIMUM', 'EQUAL', 'TEXT_MATCH', 'BOOLEAN', 'INFORMATIONAL')", name="ck_specification_limits_criterion_type"),
        CheckConstraint("sequence_number IS NULL OR sequence_number > 0", name="ck_specification_limits_sequence_positive"),
        CheckConstraint("version > 0", name="ck_specification_limits_version_positive"),
    )
    specification_test_id: Mapped[UUID] = mapped_column(ForeignKey("specification_tests.id", ondelete="RESTRICT"), nullable=False, index=True)
    parameter_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    criterion_type: Mapped[str] = mapped_column(String(20), nullable=False)
    lower_limit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    upper_limit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    target_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    text_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    boolean_value: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sequence_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    specification_test = relationship("SpecificationTest", back_populates="limits")
