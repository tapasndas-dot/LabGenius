"""Add Sprint 16 organization-owned business masters.

Revision ID: a16f04c9d821
Revises: e7a4c1d9b302
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a16f04c9d821"
down_revision: Union[str, None] = "e7a4c1d9b302"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _common_columns() -> list[sa.Column]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def _create_common_indexes(table: str) -> None:
    op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])
    op.create_index(f"ix_{table}_organization_active", table, ["organization_id", "is_active"])


def upgrade() -> None:
    op.create_table(
        "locations",
        *_common_columns(),
        sa.Column("parent_location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("location_type", sa.String(length=20), nullable=False),
        sa.CheckConstraint(
            "location_type IN ('SITE', 'BUILDING', 'AREA', 'LABORATORY', 'ROOM', 'STORAGE', 'OTHER')",
            name="ck_locations_location_type",
        ),
        sa.CheckConstraint("version > 0", name="ck_locations_version_positive"),
        sa.CheckConstraint("parent_location_id IS NULL OR parent_location_id <> id", name="ck_locations_not_self_parent"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["organization_id", "parent_location_id"],
            ["locations.organization_id", "locations.id"],
            name="fk_locations_parent_same_organization",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_locations_organization_code"),
        sa.UniqueConstraint("organization_id", "id", name="uq_locations_organization_id"),
    )
    _create_common_indexes("locations")
    op.create_index("ix_locations_parent_location_id", "locations", ["parent_location_id"])

    op.create_table(
        "manufacturers",
        *_common_columns(),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.CheckConstraint("version > 0", name="ck_manufacturers_version_positive"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_manufacturers_organization_code"),
    )
    _create_common_indexes("manufacturers")

    op.create_table(
        "instrument_types",
        *_common_columns(),
        sa.CheckConstraint("version > 0", name="ck_instrument_types_version_positive"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_instrument_types_organization_code"),
    )
    _create_common_indexes("instrument_types")

    op.create_table(
        "materials",
        *_common_columns(),
        sa.Column("material_type", sa.String(length=30), nullable=False),
        sa.Column("default_unit_of_measure", sa.String(length=50), nullable=True),
        sa.CheckConstraint(
            "material_type IN ('RAW_MATERIAL', 'PACKAGING_MATERIAL', 'INTERMEDIATE', 'BULK_PRODUCT', 'FINISHED_PRODUCT', 'REFERENCE_STANDARD', 'REAGENT', 'OTHER')",
            name="ck_materials_material_type",
        ),
        sa.CheckConstraint("version > 0", name="ck_materials_version_positive"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_materials_organization_code"),
    )
    _create_common_indexes("materials")


def downgrade() -> None:
    for table in ("materials", "instrument_types", "manufacturers"):
        op.drop_index(f"ix_{table}_organization_active", table_name=table)
        op.drop_index(f"ix_{table}_organization_id", table_name=table)
        op.drop_table(table)
    op.drop_index("ix_locations_parent_location_id", table_name="locations")
    op.drop_index("ix_locations_organization_active", table_name="locations")
    op.drop_index("ix_locations_organization_id", table_name="locations")
    op.drop_table("locations")
