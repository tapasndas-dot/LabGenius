"""Add user-role access scope

Revision ID: d40a6c87e913
Revises: b7219de4a612
Create Date: 2026-08-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d40a6c87e913"
down_revision: Union[str, Sequence[str], None] = "b7219de4a612"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_roles",
        sa.Column("access_scope", sa.String(length=30), server_default="SELF", nullable=False),
    )
    op.create_check_constraint(
        "ck_user_roles_access_scope",
        "user_roles",
        "access_scope IN ('ORGANIZATION', 'BUSINESS_UNIT', 'DIVISION', 'DEPARTMENT', 'SELF')",
    )
    op.execute(
        """
        UPDATE user_roles AS ur
        SET access_scope = 'ORGANIZATION'
        FROM roles AS r
        WHERE ur.role_id = r.id AND r.role_code = 'ADMIN'
        """
    )


def downgrade() -> None:
    op.drop_constraint("ck_user_roles_access_scope", "user_roles", type_="check")
    op.drop_column("user_roles", "access_scope")
