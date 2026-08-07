"""Standardize server defaults

Revision ID: f2cdc8af6c15
Revises: 3dac3d42e6bd
Create Date: 2026-08-07 23:48:29.407355
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2cdc8af6c15"
down_revision: Union[str, Sequence[str], None] = "3dac3d42e6bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MASTER_TABLES = [
    "organizations",
    "business_units",
    "divisions",
    "departments",
    "designations",
    "users",
    "roles",
    "permissions",
    "user_roles",
    "role_permissions",
]


def upgrade() -> None:
    """
    Standardize database defaults so ORM inserts,
    SQL inserts and Supabase inserts behave identically.
    """

    for table in MASTER_TABLES:

        op.alter_column(
            table,
            "id",
            existing_type=sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            existing_nullable=False,
        )

        op.alter_column(
            table,
            "is_active",
            existing_type=sa.Boolean(),
            server_default=sa.text("true"),
            existing_nullable=False,
        )

        op.alter_column(
            table,
            "version",
            existing_type=sa.Integer(),
            server_default=sa.text("1"),
            existing_nullable=False,
        )


def downgrade() -> None:
    """
    Remove database defaults.
    """

    for table in MASTER_TABLES:

        op.alter_column(
            table,
            "id",
            existing_type=sa.UUID(),
            server_default=None,
            existing_nullable=False,
        )

        op.alter_column(
            table,
            "is_active",
            existing_type=sa.Boolean(),
            server_default=None,
            existing_nullable=False,
        )

        op.alter_column(
            table,
            "version",
            existing_type=sa.Integer(),
            server_default=None,
            existing_nullable=False,
        )