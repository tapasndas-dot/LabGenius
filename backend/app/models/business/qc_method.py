from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseModel
from app.database.base_entities import MasterEntity
from app.database.mixins import TimestampMixin, UUIDMixin, VersionMixin


class MethodVersionStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    RETIRED = "RETIRED"
    SUPERSEDED = "SUPERSEDED"


class MethodParameterValueType(StrEnum):
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    INTEGER = "INTEGER"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    DATETIME = "DATETIME"


class Test(MasterEntity):
    __tablename__ = "qc_tests"
    __table_args__ = (
        UniqueConstraint("organization_id", "test_code", name="uq_qc_tests_organization_code"),
        CheckConstraint("version > 0", name="ck_qc_tests_version_positive"),
        Index("ix_qc_tests_organization_active", "organization_id", "is_active"),
    )
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    test_code: Mapped[str] = mapped_column(String(50), nullable=False)
    test_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)


class Method(MasterEntity):
    __tablename__ = "methods"
    __table_args__ = (
        UniqueConstraint("organization_id", "method_code", name="uq_methods_organization_code"),
        CheckConstraint("version > 0", name="ck_methods_version_positive"),
        Index("ix_methods_organization_active", "organization_id", "is_active"),
    )
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    method_code: Mapped[str] = mapped_column(String(50), nullable=False)
    method_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    method_versions = relationship("MethodVersion", back_populates="method", passive_deletes=True)


class MethodVersion(UUIDMixin, TimestampMixin, VersionMixin, BaseModel):
    __tablename__ = "method_versions"
    __table_args__ = (
        UniqueConstraint("method_id", "version_number", name="uq_method_versions_method_number"),
        CheckConstraint("version_number > 0", name="ck_method_versions_number_positive"),
        CheckConstraint("status IN ('DRAFT', 'APPROVED', 'RETIRED', 'SUPERSEDED')", name="ck_method_versions_status"),
        CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_method_versions_effectivity"),
        CheckConstraint("version > 0", name="ck_method_versions_version_positive"),
        Index("ix_method_versions_method_status", "method_id", "status"),
    )
    method_id: Mapped[UUID] = mapped_column(ForeignKey("methods.id", ondelete="RESTRICT"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=MethodVersionStatus.DRAFT, server_default=text("'DRAFT'"))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    method = relationship("Method", back_populates="method_versions")
    parameters = relationship("MethodParameter", back_populates="method_version", passive_deletes=True)


class MethodParameter(UUIDMixin, TimestampMixin, VersionMixin, BaseModel):
    __tablename__ = "method_parameters"
    __table_args__ = (
        UniqueConstraint("method_version_id", "parameter_code", name="uq_method_parameters_version_code"),
        CheckConstraint("value_type IN ('TEXT', 'NUMBER', 'INTEGER', 'BOOLEAN', 'DATE', 'DATETIME')", name="ck_method_parameters_value_type"),
        CheckConstraint("sequence_number IS NULL OR sequence_number > 0", name="ck_method_parameters_sequence_positive"),
        CheckConstraint("version > 0", name="ck_method_parameters_version_positive"),
    )
    method_version_id: Mapped[UUID] = mapped_column(ForeignKey("method_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    parameter_code: Mapped[str] = mapped_column(String(50), nullable=False)
    parameter_name: Mapped[str] = mapped_column(String(200), nullable=False)
    value_type: Mapped[str] = mapped_column(String(20), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    default_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    sequence_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    method_version = relationship("MethodVersion", back_populates="parameters")
