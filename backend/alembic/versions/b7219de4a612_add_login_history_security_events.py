"""Add login history and security events

Revision ID: b7219de4a612
Revises: f2cdc8af6c15
Create Date: 2026-08-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b7219de4a612"
down_revision: Union[str, Sequence[str], None] = "f2cdc8af6c15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "login_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("username_attempted", sa.String(length=255), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column(
            "event_timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("failure_reason", sa.String(length=50), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_login_history_user_id", "login_history", ["user_id"])
    op.create_index(
        "ix_login_history_username_attempted", "login_history", ["username_attempted"]
    )
    op.create_index("ix_login_history_success", "login_history", ["success"])
    op.create_index(
        "ix_login_history_event_timestamp", "login_history", ["event_timestamp"]
    )

    op.create_table(
        "security_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column(
            "event_timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_security_events_actor_user_id", "security_events", ["actor_user_id"]
    )
    op.create_index(
        "ix_security_events_target_user_id", "security_events", ["target_user_id"]
    )
    op.create_index("ix_security_events_event_type", "security_events", ["event_type"])
    op.create_index(
        "ix_security_events_event_timestamp", "security_events", ["event_timestamp"]
    )


def downgrade() -> None:
    op.drop_index("ix_security_events_event_timestamp", table_name="security_events")
    op.drop_index("ix_security_events_event_type", table_name="security_events")
    op.drop_index("ix_security_events_target_user_id", table_name="security_events")
    op.drop_index("ix_security_events_actor_user_id", table_name="security_events")
    op.drop_table("security_events")

    op.drop_index("ix_login_history_event_timestamp", table_name="login_history")
    op.drop_index("ix_login_history_success", table_name="login_history")
    op.drop_index("ix_login_history_username_attempted", table_name="login_history")
    op.drop_index("ix_login_history_user_id", table_name="login_history")
    op.drop_table("login_history")
