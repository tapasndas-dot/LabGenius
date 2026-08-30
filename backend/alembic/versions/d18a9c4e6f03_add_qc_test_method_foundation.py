"""Add QC Test and Method version foundation.

Revision ID: d18a9c4e6f03
Revises: c17a8f3d5e02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d18a9c4e6f03"
down_revision: str | None = "c17a8f3d5e02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _master_columns():
    return (
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )


def _versioned_columns():
    return (
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "qc_tests",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_code", sa.String(length=50), nullable=False),
        sa.Column("test_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("test_category", sa.String(length=100), nullable=True),
        sa.Column("default_unit", sa.String(length=50), nullable=True),
        *_master_columns(),
        sa.CheckConstraint("version > 0", name="ck_qc_tests_version_positive"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "test_code", name="uq_qc_tests_organization_code"),
    )
    op.create_index("ix_qc_tests_organization_id", "qc_tests", ["organization_id"])
    op.create_index("ix_qc_tests_organization_active", "qc_tests", ["organization_id", "is_active"])

    op.create_table(
        "methods",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("method_code", sa.String(length=50), nullable=False),
        sa.Column("method_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        *_master_columns(),
        sa.CheckConstraint("version > 0", name="ck_methods_version_positive"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "method_code", name="uq_methods_organization_code"),
    )
    op.create_index("ix_methods_organization_id", "methods", ["organization_id"])
    op.create_index("ix_methods_organization_active", "methods", ["organization_id", "is_active"])

    op.create_table(
        "method_versions",
        sa.Column("method_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("version_label", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="DRAFT", nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_reference", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        *_versioned_columns(),
        sa.CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_method_versions_effectivity"),
        sa.CheckConstraint("version_number > 0", name="ck_method_versions_number_positive"),
        sa.CheckConstraint("status IN ('DRAFT', 'APPROVED', 'RETIRED', 'SUPERSEDED')", name="ck_method_versions_status"),
        sa.CheckConstraint("version > 0", name="ck_method_versions_version_positive"),
        sa.ForeignKeyConstraint(["method_id"], ["methods.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("method_id", "version_number", name="uq_method_versions_method_number"),
    )
    op.create_index("ix_method_versions_method_id", "method_versions", ["method_id"])
    op.create_index("ix_method_versions_method_status", "method_versions", ["method_id", "status"])

    op.create_table(
        "method_parameters",
        sa.Column("method_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parameter_code", sa.String(length=50), nullable=False),
        sa.Column("parameter_name", sa.String(length=200), nullable=False),
        sa.Column("value_type", sa.String(length=20), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("default_value", sa.Text(), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=True),
        sa.Column("is_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        *_versioned_columns(),
        sa.CheckConstraint("sequence_number IS NULL OR sequence_number > 0", name="ck_method_parameters_sequence_positive"),
        sa.CheckConstraint("value_type IN ('TEXT', 'NUMBER', 'INTEGER', 'BOOLEAN', 'DATE', 'DATETIME')", name="ck_method_parameters_value_type"),
        sa.CheckConstraint("version > 0", name="ck_method_parameters_version_positive"),
        sa.ForeignKeyConstraint(["method_version_id"], ["method_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("method_version_id", "parameter_code", name="uq_method_parameters_version_code"),
    )
    op.create_index("ix_method_parameters_method_version_id", "method_parameters", ["method_version_id"])


def downgrade() -> None:
    op.drop_index("ix_method_parameters_method_version_id", table_name="method_parameters")
    op.drop_table("method_parameters")
    op.drop_index("ix_method_versions_method_status", table_name="method_versions")
    op.drop_index("ix_method_versions_method_id", table_name="method_versions")
    op.drop_table("method_versions")
    op.drop_index("ix_methods_organization_active", table_name="methods")
    op.drop_index("ix_methods_organization_id", table_name="methods")
    op.drop_table("methods")
    op.drop_index("ix_qc_tests_organization_active", table_name="qc_tests")
    op.drop_index("ix_qc_tests_organization_id", table_name="qc_tests")
    op.drop_table("qc_tests")
