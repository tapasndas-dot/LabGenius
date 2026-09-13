"""Add Stability Protocol and Study domain foundation.

Revision ID: 23a_stability_foundation
Revises: 21a_result_foundation
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "23a_stability_foundation"
down_revision: Union[str, Sequence[str], None] = "21a_result_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stability_protocols",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("protocol_code", sa.String(50), nullable=False),
        sa.Column("protocol_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.CheckConstraint("version > 0", name="ck_stability_protocols_version_positive"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "protocol_code", name="uq_stability_protocols_organization_code"),
    )
    for name, columns in (
        ("ix_stability_protocols_organization_active", ["organization_id", "is_active"]),
        ("ix_stability_protocols_organization_id", ["organization_id"]),
    ): op.create_index(name, "stability_protocols", columns)

    op.create_table(
        "stability_protocol_versions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("stability_protocol_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("version_label", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), server_default="DRAFT", nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.CheckConstraint("version_number > 0", name="ck_stability_protocol_versions_number_positive"),
        sa.CheckConstraint("status IN ('DRAFT', 'APPROVED', 'RETIRED', 'SUPERSEDED')", name="ck_stability_protocol_versions_status"),
        sa.CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_stability_protocol_versions_effectivity"),
        sa.CheckConstraint("version > 0", name="ck_stability_protocol_versions_version_positive"),
        sa.ForeignKeyConstraint(["stability_protocol_id"], ["stability_protocols.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stability_protocol_id", "version_number", name="uq_stability_protocol_versions_protocol_number"),
    )
    op.create_index("ix_stability_protocol_versions_stability_protocol_id", "stability_protocol_versions", ["stability_protocol_id"])

    op.create_table(
        "stability_protocol_conditions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("stability_protocol_version_id", sa.UUID(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("condition_code", sa.String(50), nullable=False),
        sa.Column("condition_name", sa.String(200), nullable=False),
        sa.Column("temperature_value", sa.Numeric(10, 3), nullable=True),
        sa.Column("temperature_unit", sa.String(20), nullable=True),
        sa.Column("temperature_tolerance", sa.Numeric(10, 3), nullable=True),
        sa.Column("humidity_value", sa.Numeric(10, 3), nullable=True),
        sa.Column("humidity_unit", sa.String(20), nullable=True),
        sa.Column("humidity_tolerance", sa.Numeric(10, 3), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.CheckConstraint("sequence_number > 0", name="ck_stability_protocol_conditions_sequence_positive"),
        sa.CheckConstraint("version > 0", name="ck_stability_protocol_conditions_version_positive"),
        sa.ForeignKeyConstraint(["stability_protocol_version_id"], ["stability_protocol_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stability_protocol_version_id", "sequence_number", name="uq_stability_protocol_conditions_version_sequence"),
        sa.UniqueConstraint("stability_protocol_version_id", "condition_code", name="uq_stability_protocol_conditions_version_code"),
    )
    op.create_index("ix_stability_protocol_conditions_stability_protocol_version_id", "stability_protocol_conditions", ["stability_protocol_version_id"])

    op.create_table(
        "stability_protocol_timepoints",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("stability_protocol_condition_id", sa.UUID(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("interval_value", sa.Integer(), nullable=True),
        sa.Column("interval_unit", sa.String(20), nullable=True),
        sa.Column("is_initial", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("specification_version_id", sa.UUID(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.CheckConstraint("sequence_number > 0", name="ck_stability_protocol_timepoints_sequence_positive"),
        sa.CheckConstraint("(is_initial AND interval_value IS NULL AND interval_unit IS NULL) OR (NOT is_initial AND interval_value > 0 AND interval_unit IN ('DAY', 'WEEK', 'MONTH', 'YEAR'))", name="ck_stability_protocol_timepoints_interval"),
        sa.CheckConstraint("version > 0", name="ck_stability_protocol_timepoints_version_positive"),
        sa.ForeignKeyConstraint(["stability_protocol_condition_id"], ["stability_protocol_conditions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["specification_version_id"], ["specification_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stability_protocol_condition_id", "sequence_number", name="uq_stability_protocol_timepoints_condition_sequence"),
    )
    op.create_index("ix_stability_timepoints_condition_id", "stability_protocol_timepoints", ["stability_protocol_condition_id"])
    op.create_index("ix_stability_protocol_timepoints_specification_version_id", "stability_protocol_timepoints", ["specification_version_id"])
    op.create_index("uq_stability_protocol_timepoints_initial", "stability_protocol_timepoints", ["stability_protocol_condition_id"], unique=True, postgresql_where=sa.text("is_initial"))

    op.create_table(
        "stability_studies",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("business_unit_id", sa.UUID(), nullable=True),
        sa.Column("division_id", sa.UUID(), nullable=True),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("study_number", sa.String(100), nullable=False),
        sa.Column("study_name", sa.String(200), nullable=False),
        sa.Column("material_id", sa.UUID(), nullable=False),
        sa.Column("batch_number", sa.String(100), nullable=True),
        sa.Column("lot_number", sa.String(100), nullable=True),
        sa.Column("stability_protocol_version_id", sa.UUID(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), server_default="DRAFT", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('DRAFT', 'ACTIVE', 'COMPLETED', 'CANCELLED')", name="ck_stability_studies_status"),
        sa.CheckConstraint("version > 0", name="ck_stability_studies_version_positive"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["business_unit_id"], ["business_units.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["division_id"], ["divisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["stability_protocol_version_id"], ["stability_protocol_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "study_number", name="uq_stability_studies_organization_number"),
    )
    for name, columns in (
        ("ix_stability_studies_organization_status", ["organization_id", "status"]),
        ("ix_stability_studies_hierarchy", ["organization_id", "business_unit_id", "division_id", "department_id"]),
        ("ix_stability_studies_organization_id", ["organization_id"]),
        ("ix_stability_studies_business_unit_id", ["business_unit_id"]),
        ("ix_stability_studies_division_id", ["division_id"]),
        ("ix_stability_studies_department_id", ["department_id"]),
        ("ix_stability_studies_material_id", ["material_id"]),
        ("ix_stability_studies_stability_protocol_version_id", ["stability_protocol_version_id"]),
    ): op.create_index(name, "stability_studies", columns)

    op.create_table(
        "stability_study_conditions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("stability_study_id", sa.UUID(), nullable=False),
        sa.Column("stability_protocol_condition_id", sa.UUID(), nullable=False),
        sa.Column("instrument_id", sa.UUID(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("ended_at IS NULL OR assigned_at IS NULL OR ended_at >= assigned_at", name="ck_stability_study_conditions_dates"),
        sa.CheckConstraint("version > 0", name="ck_stability_study_conditions_version_positive"),
        sa.ForeignKeyConstraint(["stability_study_id"], ["stability_studies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["stability_protocol_condition_id"], ["stability_protocol_conditions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stability_study_id", "stability_protocol_condition_id", name="uq_stability_study_conditions_study_protocol_condition"),
    )
    op.create_index("ix_stability_study_conditions_stability_study_id", "stability_study_conditions", ["stability_study_id"])
    op.create_index("ix_stability_study_conditions_stability_protocol_condition_id", "stability_study_conditions", ["stability_protocol_condition_id"])
    op.create_index("ix_stability_study_conditions_instrument_id", "stability_study_conditions", ["instrument_id"])


def downgrade() -> None:
    op.drop_table("stability_study_conditions")
    op.drop_table("stability_studies")
    op.drop_table("stability_protocol_timepoints")
    op.drop_table("stability_protocol_conditions")
    op.drop_table("stability_protocol_versions")
    op.drop_table("stability_protocols")
