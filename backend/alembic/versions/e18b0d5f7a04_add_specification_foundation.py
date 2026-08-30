"""Add Specification version tree foundation.

Revision ID: e18b0d5f7a04
Revises: d18a9c4e6f03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e18b0d5f7a04"
down_revision: str | None = "d18a9c4e6f03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _versioned_columns():
    return (
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "specifications",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("specification_code", sa.String(length=50), nullable=False),
        sa.Column("specification_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_versioned_columns(),
        sa.CheckConstraint("version > 0", name="ck_specifications_version_positive"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "specification_code", name="uq_specifications_organization_code"),
    )
    op.create_index("ix_specifications_material_id", "specifications", ["material_id"])
    op.create_index("ix_specifications_organization_id", "specifications", ["organization_id"])
    op.create_index("ix_specifications_organization_active", "specifications", ["organization_id", "is_active"])

    op.create_table(
        "specification_versions",
        sa.Column("specification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("version_label", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="DRAFT", nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        *_versioned_columns(),
        sa.CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_specification_versions_effectivity"),
        sa.CheckConstraint("version_number > 0", name="ck_specification_versions_number_positive"),
        sa.CheckConstraint("status IN ('DRAFT', 'APPROVED', 'RETIRED', 'SUPERSEDED')", name="ck_specification_versions_status"),
        sa.CheckConstraint("version > 0", name="ck_specification_versions_version_positive"),
        sa.ForeignKeyConstraint(["specification_id"], ["specifications.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("specification_id", "version_number", name="uq_specification_versions_specification_number"),
    )
    op.create_index("ix_specification_versions_specification_id", "specification_versions", ["specification_id"])

    op.create_table(
        "specification_tests",
        sa.Column("specification_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("method_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("is_required", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
        *_versioned_columns(),
        sa.CheckConstraint("sequence_number > 0", name="ck_specification_tests_sequence_positive"),
        sa.CheckConstraint("version > 0", name="ck_specification_tests_version_positive"),
        sa.ForeignKeyConstraint(["method_version_id"], ["method_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["specification_version_id"], ["specification_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["test_id"], ["qc_tests.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("specification_version_id", "sequence_number", name="uq_specification_tests_version_sequence"),
        sa.UniqueConstraint("specification_version_id", "test_id", name="uq_specification_tests_version_test"),
    )
    op.create_index("ix_specification_tests_method_version_id", "specification_tests", ["method_version_id"])
    op.create_index("ix_specification_tests_specification_version_id", "specification_tests", ["specification_version_id"])
    op.create_index("ix_specification_tests_test_id", "specification_tests", ["test_id"])

    op.create_table(
        "specification_limits",
        sa.Column("specification_test_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parameter_name", sa.String(length=200), nullable=True),
        sa.Column("criterion_type", sa.String(length=20), nullable=False),
        sa.Column("lower_limit", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("upper_limit", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("target_value", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("text_value", sa.Text(), nullable=True),
        sa.Column("boolean_value", sa.Boolean(), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        *_versioned_columns(),
        sa.CheckConstraint("criterion_type IN ('BETWEEN', 'MINIMUM', 'MAXIMUM', 'EQUAL', 'TEXT_MATCH', 'BOOLEAN', 'INFORMATIONAL')", name="ck_specification_limits_criterion_type"),
        sa.CheckConstraint("sequence_number IS NULL OR sequence_number > 0", name="ck_specification_limits_sequence_positive"),
        sa.CheckConstraint("version > 0", name="ck_specification_limits_version_positive"),
        sa.ForeignKeyConstraint(["specification_test_id"], ["specification_tests.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_specification_limits_specification_test_id", "specification_limits", ["specification_test_id"])


def downgrade() -> None:
    op.drop_index("ix_specification_limits_specification_test_id", table_name="specification_limits")
    op.drop_table("specification_limits")
    op.drop_index("ix_specification_tests_test_id", table_name="specification_tests")
    op.drop_index("ix_specification_tests_specification_version_id", table_name="specification_tests")
    op.drop_index("ix_specification_tests_method_version_id", table_name="specification_tests")
    op.drop_table("specification_tests")
    op.drop_index("ix_specification_versions_specification_id", table_name="specification_versions")
    op.drop_table("specification_versions")
    op.drop_index("ix_specifications_organization_active", table_name="specifications")
    op.drop_index("ix_specifications_organization_id", table_name="specifications")
    op.drop_index("ix_specifications_material_id", table_name="specifications")
    op.drop_table("specifications")
