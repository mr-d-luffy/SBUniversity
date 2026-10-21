"""Add audio attachments to community chat messages.

Revision ID: 012_chat_voice_messages
Revises: 011_admin_course_management
Create Date: 2026-10-22
"""
from alembic import op
import sqlalchemy as sa

revision = "012_chat_voice_messages"
down_revision = "011_admin_course_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "community_messages", sa.Column("audio_path", sa.String(length=512), nullable=True)
    )
    op.add_column(
        "community_messages", sa.Column("audio_mime_type", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "community_messages", sa.Column("audio_size_bytes", sa.Integer(), nullable=True)
    )
    op.create_check_constraint(
        "ck_community_message_audio_size",
        "community_messages",
        "audio_size_bytes IS NULL OR "
        "(audio_size_bytes > 0 AND audio_size_bytes <= 26214400)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_community_message_audio_size", "community_messages", type_="check"
    )
    op.drop_column("community_messages", "audio_size_bytes")
    op.drop_column("community_messages", "audio_mime_type")
    op.drop_column("community_messages", "audio_path")
