"""Add verification status to teacher profiles.

Revision ID: 014_teacher_verification_status
Revises: 013_student_academic_verification
Create Date: 2026-10-23
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "014_teacher_verification_status"
down_revision = "013_student_academic_verification"
branch_labels = None
depends_on = None


verification_status = postgresql.ENUM(
    "not_verified",
    "verified",
    name="user_verification_status",
    create_type=False,
)


def upgrade() -> None:
    op.add_column(
        "teacher_profiles",
        sa.Column(
            "verification_status",
            verification_status,
            server_default="not_verified",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("teacher_profiles", "verification_status")
