from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseModel
from app.database.base_entities import MasterEntity
from app.database.mixins import TimestampMixin, UUIDMixin, VersionMixin


class StabilityProtocolVersionStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    RETIRED = "RETIRED"
    SUPERSEDED = "SUPERSEDED"


class StabilityStudyStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class StabilityProtocol(MasterEntity):
    __tablename__ = "stability_protocols"
    __table_args__ = (
        UniqueConstraint("organization_id", "protocol_code", name="uq_stability_protocols_organization_code"),
        CheckConstraint("version > 0", name="ck_stability_protocols_version_positive"),
        Index("ix_stability_protocols_organization_active", "organization_id", "is_active"),
    )
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    protocol_code: Mapped[str] = mapped_column(String(50), nullable=False)
    protocol_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    versions = relationship("StabilityProtocolVersion", back_populates="protocol", passive_deletes=True)


class StabilityProtocolVersion(UUIDMixin, TimestampMixin, VersionMixin, BaseModel):
    __tablename__ = "stability_protocol_versions"
    __table_args__ = (
        UniqueConstraint("stability_protocol_id", "version_number", name="uq_stability_protocol_versions_protocol_number"),
        CheckConstraint("version_number > 0", name="ck_stability_protocol_versions_number_positive"),
        CheckConstraint("status IN ('DRAFT', 'APPROVED', 'RETIRED', 'SUPERSEDED')", name="ck_stability_protocol_versions_status"),
        CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_stability_protocol_versions_effectivity"),
        CheckConstraint("version > 0", name="ck_stability_protocol_versions_version_positive"),
    )
    stability_protocol_id: Mapped[UUID] = mapped_column(ForeignKey("stability_protocols.id", ondelete="RESTRICT"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=StabilityProtocolVersionStatus.DRAFT, server_default=text("'DRAFT'"))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    protocol = relationship("StabilityProtocol", back_populates="versions")
    conditions = relationship("StabilityProtocolCondition", back_populates="protocol_version", passive_deletes=True)


class StabilityProtocolCondition(UUIDMixin, TimestampMixin, VersionMixin, BaseModel):
    __tablename__ = "stability_protocol_conditions"
    __table_args__ = (
        UniqueConstraint("stability_protocol_version_id", "sequence_number", name="uq_stability_protocol_conditions_version_sequence"),
        UniqueConstraint("stability_protocol_version_id", "condition_code", name="uq_stability_protocol_conditions_version_code"),
        CheckConstraint("sequence_number > 0", name="ck_stability_protocol_conditions_sequence_positive"),
        CheckConstraint("version > 0", name="ck_stability_protocol_conditions_version_positive"),
    )
    stability_protocol_version_id: Mapped[UUID] = mapped_column(ForeignKey("stability_protocol_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    condition_code: Mapped[str] = mapped_column(String(50), nullable=False)
    condition_name: Mapped[str] = mapped_column(String(200), nullable=False)
    temperature_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    temperature_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    temperature_tolerance: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    humidity_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    humidity_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    humidity_tolerance: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    protocol_version = relationship("StabilityProtocolVersion", back_populates="conditions")
    timepoints = relationship("StabilityProtocolTimepoint", back_populates="condition", passive_deletes=True)


class StabilityProtocolTimepoint(UUIDMixin, TimestampMixin, VersionMixin, BaseModel):
    __tablename__ = "stability_protocol_timepoints"
    __table_args__ = (
        UniqueConstraint("stability_protocol_condition_id", "sequence_number", name="uq_stability_protocol_timepoints_condition_sequence"),
        Index("uq_stability_protocol_timepoints_initial", "stability_protocol_condition_id", unique=True, postgresql_where=text("is_initial")),
        Index("ix_stability_timepoints_condition_id", "stability_protocol_condition_id"),
        CheckConstraint("sequence_number > 0", name="ck_stability_protocol_timepoints_sequence_positive"),
        CheckConstraint("(is_initial AND interval_value IS NULL AND interval_unit IS NULL) OR (NOT is_initial AND interval_value > 0 AND interval_unit IN ('DAY', 'WEEK', 'MONTH', 'YEAR'))", name="ck_stability_protocol_timepoints_interval"),
        CheckConstraint("version > 0", name="ck_stability_protocol_timepoints_version_positive"),
    )
    stability_protocol_condition_id: Mapped[UUID] = mapped_column(ForeignKey("stability_protocol_conditions.id", ondelete="RESTRICT"), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    interval_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interval_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_initial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    specification_version_id: Mapped[UUID] = mapped_column(ForeignKey("specification_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition = relationship("StabilityProtocolCondition", back_populates="timepoints")


class StabilityStudy(UUIDMixin, TimestampMixin, VersionMixin, BaseModel):
    __tablename__ = "stability_studies"
    __table_args__ = (
        UniqueConstraint("organization_id", "study_number", name="uq_stability_studies_organization_number"),
        CheckConstraint("status IN ('DRAFT', 'ACTIVE', 'COMPLETED', 'CANCELLED')", name="ck_stability_studies_status"),
        CheckConstraint("version > 0", name="ck_stability_studies_version_positive"),
        Index("ix_stability_studies_organization_status", "organization_id", "status"),
        Index("ix_stability_studies_hierarchy", "organization_id", "business_unit_id", "division_id", "department_id"),
    )
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    business_unit_id: Mapped[UUID | None] = mapped_column(ForeignKey("business_units.id", ondelete="RESTRICT"), nullable=True, index=True)
    division_id: Mapped[UUID | None] = mapped_column(ForeignKey("divisions.id", ondelete="RESTRICT"), nullable=True, index=True)
    department_id: Mapped[UUID | None] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=True, index=True)
    study_number: Mapped[str] = mapped_column(String(100), nullable=False)
    study_name: Mapped[str] = mapped_column(String(200), nullable=False)
    material_id: Mapped[UUID] = mapped_column(ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False, index=True)
    stability_protocol_version_id: Mapped[UUID] = mapped_column(ForeignKey("stability_protocol_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=StabilityStudyStatus.DRAFT, server_default=text("'DRAFT'"))
    batch_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lot_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    protocol_version = relationship("StabilityProtocolVersion")
    conditions = relationship("StabilityStudyCondition", back_populates="study", passive_deletes=True)


class StabilityStudyCondition(UUIDMixin, TimestampMixin, VersionMixin, BaseModel):
    __tablename__ = "stability_study_conditions"
    __table_args__ = (
        UniqueConstraint("stability_study_id", "stability_protocol_condition_id", name="uq_stability_study_conditions_study_protocol_condition"),
        CheckConstraint("ended_at IS NULL OR assigned_at IS NULL OR ended_at >= assigned_at", name="ck_stability_study_conditions_dates"),
        CheckConstraint("version > 0", name="ck_stability_study_conditions_version_positive"),
    )
    stability_study_id: Mapped[UUID] = mapped_column(ForeignKey("stability_studies.id", ondelete="RESTRICT"), nullable=False, index=True)
    stability_protocol_condition_id: Mapped[UUID] = mapped_column(ForeignKey("stability_protocol_conditions.id", ondelete="RESTRICT"), nullable=False, index=True)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    study = relationship("StabilityStudy", back_populates="conditions")
    protocol_condition = relationship("StabilityProtocolCondition")
    instrument = relationship("Instrument")
