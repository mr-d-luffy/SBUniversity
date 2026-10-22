"""Add student academic term and verification status.

Revision ID: 013_student_academic_verification
Revises: 012_chat_voice_messages
Create Date: 2026-10-23
"""
from alembic import op
import sqlalchemy as sa


revision = "013_student_academic_verification"
down_revision = "012_chat_voice_messages"
branch_labels = None
depends_on = None


verification_status = sa.Enum(
    "not_verified",
    "verified",
    name="user_verification_status",
)


def upgrade() -> None:
    verification_status.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "student_profiles",
        sa.Column("academic_term", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "student_profiles",
        sa.Column(
            "verification_status",
            verification_status,
            server_default="not_verified",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("student_profiles", "verification_status")
    op.drop_column("student_profiles", "academic_term")
    verification_status.drop(op.get_bind(), checkfirst=True)
