from enum import StrEnum
from uuid import UUID
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseModel
from app.database.base_entities import MasterEntity
from app.database.mixins import TimestampMixin, UUIDMixin, VersionMixin


class InstrumentStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    IN_USE = "IN_USE"
    UNDER_CALIBRATION = "UNDER_CALIBRATION"
    UNDER_MAINTENANCE = "UNDER_MAINTENANCE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"
    QUALIFICATION_PENDING = "QUALIFICATION_PENDING"
    RETIRED = "RETIRED"


class InstrumentCriticality(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Instrument(MasterEntity):
    __tablename__ = "instruments"
    __table_args__ = (
        UniqueConstraint("organization_id", "instrument_code", name="uq_instruments_organization_code"),
        CheckConstraint("status IN ('AVAILABLE', 'IN_USE', 'UNDER_CALIBRATION', 'UNDER_MAINTENANCE', 'OUT_OF_SERVICE', 'QUALIFICATION_PENDING', 'RETIRED')", name="ck_instruments_status"),
        CheckConstraint("criticality IS NULL OR criticality IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name="ck_instruments_criticality"),
        CheckConstraint("version > 0", name="ck_instruments_version_positive"),
        Index("ix_instruments_organization_active", "organization_id", "is_active"),
        Index("ix_instruments_organization_status", "organization_id", "status"),
    )
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    business_unit_id: Mapped[UUID | None] = mapped_column(ForeignKey("business_units.id", ondelete="RESTRICT"), nullable=True, index=True)
    division_id: Mapped[UUID | None] = mapped_column(ForeignKey("divisions.id", ondelete="RESTRICT"), nullable=True, index=True)
    department_id: Mapped[UUID | None] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=True, index=True)
    instrument_type_id: Mapped[UUID] = mapped_column(ForeignKey("instrument_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    manufacturer_id: Mapped[UUID | None] = mapped_column(ForeignKey("manufacturers.id", ondelete="RESTRICT"), nullable=True, index=True)
    location_id: Mapped[UUID | None] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"), nullable=True, index=True)
    responsible_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)
    instrument_code: Mapped[str] = mapped_column(String(50), nullable=False)
    instrument_name: Mapped[str] = mapped_column(String(200), nullable=False)
    model_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=InstrumentStatus.AVAILABLE, server_default=text("'AVAILABLE'"))
    criticality: Mapped[str | None] = mapped_column(String(20), nullable=True)
    calibration_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    maintenance_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    qualification_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    chamber_profile = relationship("StabilityChamberProfile", back_populates="instrument", uselist=False, passive_deletes=True)


class StabilityChamberProfile(UUIDMixin, TimestampMixin, VersionMixin, BaseModel):
    __tablename__ = "stability_chamber_profiles"
    __table_args__ = (CheckConstraint("version > 0", name="ck_stability_chamber_profiles_version_positive"),)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True)
    temperature_setpoint: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    temperature_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    humidity_setpoint: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    humidity_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    instrument = relationship("Instrument", back_populates="chamber_profile")
