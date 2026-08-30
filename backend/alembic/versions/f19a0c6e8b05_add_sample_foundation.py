"""Add Sample and SampleTest foundation.

Revision ID: f19a0c6e8b05
Revises: e18b0d5f7a04
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f19a0c6e8b05"
down_revision: str | None = "e18b0d5f7a04"
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
        "qc_samples",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("division_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sample_number", sa.String(100), nullable=False),
        sa.Column("external_reference", sa.String(200), nullable=True),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("specification_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sample_description", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=True),
        sa.Column("quantity_unit", sa.String(50), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sampled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), server_default="REGISTERED", nullable=False),
        sa.Column("priority", sa.String(20), server_default="NORMAL", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *_versioned_columns(),
        sa.CheckConstraint("status IN ('REGISTERED', 'IN_TESTING', 'REVIEW', 'FINALIZED', 'CANCELLED')", name="ck_qc_samples_status"),
        sa.CheckConstraint("priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')", name="ck_qc_samples_priority"),
        sa.CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_qc_samples_quantity_positive"),
        sa.CheckConstraint("version > 0", name="ck_qc_samples_version_positive"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["business_unit_id"], ["business_units.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["division_id"], ["divisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["specification_version_id"], ["specification_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "sample_number", name="uq_qc_samples_organization_number"),
    )
    for column in ("organization_id", "business_unit_id", "division_id", "department_id", "material_id", "specification_version_id"):
        op.create_index(f"ix_qc_samples_{column}", "qc_samples", [column])
    op.create_index("ix_qc_samples_organization_status", "qc_samples", ["organization_id", "status"])
    op.create_index("ix_qc_samples_hierarchy", "qc_samples", ["organization_id", "business_unit_id", "division_id", "department_id"])

    op.create_table(
        "sample_tests",
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("specification_test_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("method_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="PENDING", nullable=False),
        sa.Column("is_required", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=True),
        *_versioned_columns(),
        sa.CheckConstraint("sequence_number > 0", name="ck_sample_tests_sequence_positive"),
        sa.CheckConstraint("status IN ('PENDING', 'ASSIGNED', 'IN_PROGRESS', 'RESULT_ENTERED', 'REVIEWED', 'FINALIZED', 'CANCELLED')", name="ck_sample_tests_status"),
        sa.CheckConstraint("version > 0", name="ck_sample_tests_version_positive"),
        sa.ForeignKeyConstraint(["sample_id"], ["qc_samples.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["specification_test_id"], ["specification_tests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["test_id"], ["qc_tests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["method_version_id"], ["method_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sample_id", "specification_test_id", name="uq_sample_tests_sample_specification_test"),
    )
    for column in ("sample_id", "specification_test_id", "test_id", "method_version_id"):
        op.create_index(f"ix_sample_tests_{column}", "sample_tests", [column])
    op.create_index("ix_sample_tests_sample_status", "sample_tests", ["sample_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_sample_tests_sample_status", table_name="sample_tests")
    for column in ("method_version_id", "test_id", "specification_test_id", "sample_id"):
        op.drop_index(f"ix_sample_tests_{column}", table_name="sample_tests")
    op.drop_table("sample_tests")
    op.drop_index("ix_qc_samples_hierarchy", table_name="qc_samples")
    op.drop_index("ix_qc_samples_organization_status", table_name="qc_samples")
    for column in ("specification_version_id", "material_id", "department_id", "division_id", "business_unit_id", "organization_id"):
        op.drop_index(f"ix_qc_samples_{column}", table_name="qc_samples")
    op.drop_table("qc_samples")
