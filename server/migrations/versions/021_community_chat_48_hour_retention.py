"""Extend community chat inactivity retention to 48 hours.

Revision ID: 021_community_chat_48_hour_retention
Revises: 020_course_access_keys
Create Date: 2026-11-04
"""
from alembic import op

revision = "021_community_chat_48_hour_retention"
down_revision = "020_course_access_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE community_conversations "
        "SET expires_at = updated_at + INTERVAL '48 hours'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE community_conversations "
        "SET expires_at = updated_at + INTERVAL '10 hours'"
    )
