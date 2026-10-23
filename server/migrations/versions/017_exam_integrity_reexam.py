"""Flag integrity violations and allow faculty-approved re-exams.

Revision ID: 017_exam_integrity_reexam
Revises: 016_user_activity_days
Create Date: 2026-10-24
"""
from alembic import op
import sqlalchemy as sa


revision = "017_exam_integrity_reexam"
down_revision = "016_user_activity_days"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "exam_attempts",
        sa.Column("integrity_violation", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "exam_attempts",
        sa.Column("integrity_violation_reason", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "exam_attempts",
        sa.Column("integrity_flagged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "exam_attempts",
        sa.Column("reexam_approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "exam_attempts",
        sa.Column("reexam_approved_by_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_exam_attempts_reexam_approved_by_id_users",
        "exam_attempts",
        "users",
        ["reexam_approved_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_exam_attempts_integrity_violation",
        "exam_attempts",
        ["integrity_violation"],
    )


def downgrade() -> None:
    op.drop_index("ix_exam_attempts_integrity_violation", table_name="exam_attempts")
    op.drop_constraint("fk_exam_attempts_reexam_approved_by_id_users", "exam_attempts", type_="foreignkey")
    op.drop_column("exam_attempts", "reexam_approved_by_id")
    op.drop_column("exam_attempts", "reexam_approved_at")
    op.drop_column("exam_attempts", "integrity_flagged_at")
    op.drop_column("exam_attempts", "integrity_violation_reason")
    op.drop_column("exam_attempts", "integrity_violation")
