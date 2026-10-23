"""Store privacy-minimal request and portal navigation events.

Revision ID: 018_security_request_events
Revises: 017_exam_integrity_reexam
Create Date: 2026-10-24
"""
from alembic import op
import sqlalchemy as sa


revision = "018_security_request_events"
down_revision = "017_exam_integrity_reexam"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "security_request_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("path", sa.String(length=240), nullable=False),
        sa.Column("method", sa.String(length=8), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("client_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=240), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_request_events_actor_id", "security_request_events", ["actor_id"])
    op.create_index("ix_security_request_events_path", "security_request_events", ["path"])
    op.create_index("ix_security_request_events_created_at", "security_request_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_security_request_events_created_at", table_name="security_request_events")
    op.drop_index("ix_security_request_events_path", table_name="security_request_events")
    op.drop_index("ix_security_request_events_actor_id", table_name="security_request_events")
    op.drop_table("security_request_events")
