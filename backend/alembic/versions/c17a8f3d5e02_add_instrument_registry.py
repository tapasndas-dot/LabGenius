"""Add the Instrument Registry domain foundation.

Revision ID: c17a8f3d5e02
Revises: b16d7e2a4c01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c17a8f3d5e02"
down_revision: str | None = "b16d7e2a4c01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("division_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("instrument_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("manufacturer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("responsible_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("instrument_code", sa.String(length=50), nullable=False),
        sa.Column("instrument_name", sa.String(length=200), nullable=False),
        sa.Column("model_number", sa.String(length=100), nullable=True),
        sa.Column("serial_number", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="AVAILABLE", nullable=False),
        sa.Column("criticality", sa.String(length=20), nullable=True),
        sa.Column("calibration_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("maintenance_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("qualification_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint("criticality IS NULL OR criticality IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name="ck_instruments_criticality"),
        sa.CheckConstraint("status IN ('AVAILABLE', 'IN_USE', 'UNDER_CALIBRATION', 'UNDER_MAINTENANCE', 'OUT_OF_SERVICE', 'QUALIFICATION_PENDING', 'RETIRED')", name="ck_instruments_status"),
        sa.CheckConstraint("version > 0", name="ck_instruments_version_positive"),
        sa.ForeignKeyConstraint(["business_unit_id"], ["business_units.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["division_id"], ["divisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["instrument_type_id"], ["instrument_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["manufacturer_id"], ["manufacturers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "instrument_code", name="uq_instruments_organization_code"),
    )
    for column in (
        "business_unit_id", "department_id", "division_id", "instrument_type_id",
        "location_id", "manufacturer_id", "organization_id", "responsible_user_id",
    ):
        op.create_index(f"ix_instruments_{column}", "instruments", [column])
    op.create_index("ix_instruments_organization_active", "instruments", ["organization_id", "is_active"])
    op.create_index("ix_instruments_organization_status", "instruments", ["organization_id", "status"])

    op.create_table(
        "stability_chamber_profiles",
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("temperature_setpoint", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column("temperature_unit", sa.String(length=20), nullable=True),
        sa.Column("humidity_setpoint", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column("humidity_unit", sa.String(length=20), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint("version > 0", name="ck_stability_chamber_profiles_version_positive"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_stability_chamber_profiles_instrument_id",
        "stability_chamber_profiles",
        ["instrument_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_stability_chamber_profiles_instrument_id", table_name="stability_chamber_profiles")
    op.drop_table("stability_chamber_profiles")
    op.drop_index("ix_instruments_organization_status", table_name="instruments")
    op.drop_index("ix_instruments_organization_active", table_name="instruments")
    for column in reversed((
        "business_unit_id", "department_id", "division_id", "instrument_type_id",
        "location_id", "manufacturer_id", "organization_id", "responsible_user_id",
    )):
        op.drop_index(f"ix_instruments_{column}", table_name="instruments")
    op.drop_table("instruments")
