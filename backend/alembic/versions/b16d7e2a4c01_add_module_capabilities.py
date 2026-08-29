"""Add module capability foundation.

Revision ID: b16d7e2a4c01
Revises: a16f04c9d821
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b16d7e2a4c01"
down_revision: Union[str, None] = "a16f04c9d821"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MODULES = (
    ("PLATFORM", "Platform", "Authentication, security, organization hierarchy, audit, and common services.", "PLATFORM", True),
    ("CORE_LAB", "Core Lab", "Shared laboratory masters and common testing foundation.", "CORE_LAB", True),
    ("INSTRUMENTS", "Instrument / Asset Registry", "Shared instrument and asset registry capability.", "OPTIONAL_SHARED", False),
    ("STABILITY", "Stability", "Stability protocol, study, chamber, and pull capability.", "OPTIONAL_DOMAIN", False),
    ("CALIBRATION", "Calibration", "Instrument calibration capability.", "OPTIONAL_DOMAIN", False),
    ("MAINTENANCE", "Maintenance", "Instrument maintenance capability.", "OPTIONAL_DOMAIN", False),
    ("QUALIFICATION", "Qualification", "Instrument qualification capability.", "OPTIONAL_DOMAIN", False),
    ("INVENTORY", "Inventory", "Independent laboratory inventory capability.", "OPTIONAL_DOMAIN", False),
    ("CONTRACT_TESTING", "Contract Testing", "Contract laboratory submission and reporting extension.", "OPTIONAL_DOMAIN", False),
)

def _master_columns():
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]

def upgrade() -> None:
    op.create_table(
        "modules", *_master_columns(),
        sa.Column("code", sa.String(50), nullable=False), sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.String(500), nullable=True), sa.Column("capability_class", sa.String(30), nullable=False),
        sa.Column("is_core", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint("capability_class IN ('PLATFORM', 'CORE_LAB', 'OPTIONAL_SHARED', 'OPTIONAL_DOMAIN')", name="ck_modules_capability_class"),
        sa.CheckConstraint("version > 0", name="ck_modules_version_positive"), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_modules_code", "modules", ["code"], unique=True)
    op.create_table(
        "organization_modules", *_master_columns(),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("module_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("enabled_at", sa.DateTime(timezone=True), nullable=True), sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("version > 0", name="ck_organization_modules_version_positive"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["module_id"], ["modules.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("organization_id", "module_id", name="uq_organization_modules_organization_module"),
    )
    op.create_index("ix_organization_modules_organization_id", "organization_modules", ["organization_id"])
    op.create_index("ix_organization_modules_module_id", "organization_modules", ["module_id"])
    modules = sa.table("modules", sa.column("code"), sa.column("name"), sa.column("description"), sa.column("capability_class"), sa.column("is_core"))
    op.bulk_insert(modules, [dict(zip(("code", "name", "description", "capability_class", "is_core"), row)) for row in MODULES])

def downgrade() -> None:
    op.drop_index("ix_organization_modules_module_id", table_name="organization_modules")
    op.drop_index("ix_organization_modules_organization_id", table_name="organization_modules")
    op.drop_table("organization_modules")
    op.drop_index("ix_modules_code", table_name="modules")
    op.drop_table("modules")
