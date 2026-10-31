"""Add persistent end-to-end encryption keys for community chat.

Revision ID: 019_community_chat_e2ee
Revises: 018_security_request_events
Create Date: 2026-10-31
"""
import sqlalchemy as sa
from alembic import op

revision = "019_community_chat_e2ee"
down_revision = "018_security_request_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_community_message_content_length",
        "community_messages",
        type_="check",
    )
    op.create_check_constraint(
        "ck_community_message_content_length",
        "community_messages",
        "length(content) > 0 AND length(content) <= 16384",
    )
    op.drop_constraint(
        "ck_community_message_audio_size",
        "community_messages",
        type_="check",
    )
    op.create_check_constraint(
        "ck_community_message_audio_size",
        "community_messages",
        "audio_size_bytes IS NULL OR "
        "(audio_size_bytes > 0 AND audio_size_bytes <= 26214528)",
    )
    op.create_table(
        "community_chat_devices",
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("device_id"),
    )
    op.create_index(
        "ix_community_chat_devices_user_id",
        "community_chat_devices",
        ["user_id"],
    )
    op.create_table(
        "community_conversation_key_envelopes",
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("key_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("wrapped_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "length(wrapped_key) > 0 AND length(wrapped_key) <= 4096",
            name="ck_community_key_envelope_size",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["community_conversations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["device_id"], ["community_chat_devices.device_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("conversation_id", "key_id", "device_id"),
    )
    op.create_index(
        "ix_community_conversation_key_envelopes_device_id",
        "community_conversation_key_envelopes",
        ["device_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_community_conversation_key_envelopes_device_id",
        table_name="community_conversation_key_envelopes",
    )
    op.drop_table("community_conversation_key_envelopes")
    op.drop_index("ix_community_chat_devices_user_id", table_name="community_chat_devices")
    op.drop_table("community_chat_devices")
    op.drop_constraint(
        "ck_community_message_audio_size",
        "community_messages",
        type_="check",
    )
    op.create_check_constraint(
        "ck_community_message_audio_size",
        "community_messages",
        "audio_size_bytes IS NULL OR "
        "(audio_size_bytes > 0 AND audio_size_bytes <= 26214400)",
    )
    op.drop_constraint(
        "ck_community_message_content_length",
        "community_messages",
        type_="check",
    )
    op.create_check_constraint(
        "ck_community_message_content_length",
        "community_messages",
        "length(content) > 0 AND length(content) <= 16384",
    )
