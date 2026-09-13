"""Add Stability Pull scheduling foundation.

Revision ID: 24a_stability_pull_scheduling
Revises: 23a_stability_foundation
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "24a_stability_pull_scheduling"
down_revision: Union[str, Sequence[str], None] = "23a_stability_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stability_pulls",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("stability_study_id", sa.UUID(), nullable=False),
        sa.Column("stability_study_condition_id", sa.UUID(), nullable=False),
        sa.Column("stability_protocol_timepoint_id", sa.UUID(), nullable=False),
        sa.Column("specification_version_id", sa.UUID(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), server_default="SCHEDULED", nullable=False),
        sa.Column("qc_sample_id", sa.UUID(), nullable=True),
        sa.Column("pulled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('SCHEDULED', 'PULLED', 'SAMPLE_CREATED', 'CANCELLED')",
            name="ck_stability_pulls_status",
        ),
        sa.CheckConstraint("version > 0", name="ck_stability_pulls_version_positive"),
        sa.ForeignKeyConstraint(["stability_study_id"], ["stability_studies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["stability_study_condition_id"], ["stability_study_conditions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["stability_protocol_timepoint_id"], ["stability_protocol_timepoints.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["specification_version_id"], ["specification_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["qc_sample_id"], ["qc_samples.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stability_study_condition_id", "stability_protocol_timepoint_id", name="uq_stability_pulls_condition_timepoint"),
        sa.UniqueConstraint("qc_sample_id", name="uq_stability_pulls_qc_sample"),
    )
    for name, columns in (
        ("ix_stability_pulls_stability_study_id", ["stability_study_id"]),
        ("ix_stability_pulls_stability_study_condition_id", ["stability_study_condition_id"]),
        ("ix_stability_pulls_stability_protocol_timepoint_id", ["stability_protocol_timepoint_id"]),
        ("ix_stability_pulls_specification_version_id", ["specification_version_id"]),
        ("ix_stability_pulls_qc_sample_id", ["qc_sample_id"]),
        ("ix_stability_pulls_study_status", ["stability_study_id", "status"]),
    ):
        op.create_index(name, "stability_pulls", columns)


def downgrade() -> None:
    op.drop_table("stability_pulls")
