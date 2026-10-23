"""Persist daily foreground time and streak badge claims.

Revision ID: 016_user_activity_days
Revises: 015_teacher_profile_backfill
Create Date: 2026-10-24
"""
import sqlalchemy as sa
from alembic import op


revision = "016_user_activity_days"
down_revision = "015_teacher_profile_backfill"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_activity_days",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("active_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("streak_badge_collected", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "activity_date"),
        sa.CheckConstraint("active_seconds >= 0", name="ck_user_activity_days_active_seconds_nonnegative"),
    )
    op.create_index(
        "ix_user_activity_days_date",
        "user_activity_days",
        ["activity_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_activity_days_date", table_name="user_activity_days")
    op.drop_table("user_activity_days")
