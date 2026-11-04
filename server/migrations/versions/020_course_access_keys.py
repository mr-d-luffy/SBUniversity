"""Add paid course access and one-time activation keys.

Revision ID: 020_course_access_keys
Revises: 019_community_chat_e2ee
Create Date: 2026-11-04
"""
import sqlalchemy as sa
from alembic import op


revision = "020_course_access_keys"
down_revision = "019_community_chat_e2ee"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "courses",
        sa.Column("price", sa.Numeric(10, 2), server_default="0.00", nullable=False),
    )
    op.add_column(
        "courses",
        sa.Column("discount_percent", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_check_constraint(
        "ck_courses_price_nonnegative",
        "courses",
        "price >= 0",
    )
    op.create_check_constraint(
        "ck_courses_discount_percent",
        "courses",
        "discount_percent >= 0 AND discount_percent <= 100",
    )
    op.create_table(
        "course_key_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                "activated",
                name="course_key_request_status",
            ),
            nullable=False,
        ),
        sa.Column("access_key", sa.String(length=16), nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("access_key"),
    )
    op.create_index(
        "ix_course_key_requests_student_status",
        "course_key_requests",
        ["student_id", "status"],
    )
    op.create_index(
        "uq_course_key_requests_pending_student_course",
        "course_key_requests",
        ["student_id", "course_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_table(
        "course_unlocks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column(
            "unlocked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["course_key_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
        sa.UniqueConstraint(
            "student_id", "course_id", name="uq_course_unlock_student_course"
        ),
    )
    op.create_index("ix_course_unlocks_student_id", "course_unlocks", ["student_id"])
    op.create_index("ix_course_unlocks_course_id", "course_unlocks", ["course_id"])


def downgrade() -> None:
    op.drop_index("ix_course_unlocks_course_id", table_name="course_unlocks")
    op.drop_index("ix_course_unlocks_student_id", table_name="course_unlocks")
    op.drop_table("course_unlocks")
    op.drop_index(
        "ix_course_key_requests_student_status", table_name="course_key_requests"
    )
    op.drop_index(
        "uq_course_key_requests_pending_student_course",
        table_name="course_key_requests",
    )
    op.drop_table("course_key_requests")
    op.drop_constraint("ck_courses_discount_percent", "courses", type_="check")
    op.drop_constraint("ck_courses_price_nonnegative", "courses", type_="check")
    op.drop_column("courses", "discount_percent")
    op.drop_column("courses", "price")
