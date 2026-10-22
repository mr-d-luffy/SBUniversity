"""Create teacher profiles for existing teacher accounts missing one.

Revision ID: 015_teacher_profile_backfill
Revises: 014_teacher_verification_status
Create Date: 2026-10-23
"""
from alembic import op


revision = "015_teacher_profile_backfill"
down_revision = "014_teacher_verification_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO teacher_profiles (user_id, employee_code, department_id)
        SELECT users.id,
               'T-' || upper(substr(replace(users.id::text, '-', ''), 1, 12)),
               student_profiles.department_id
        FROM users
        LEFT JOIN student_profiles ON student_profiles.user_id = users.id
        WHERE users.role = 'teacher'
          AND NOT EXISTS (
              SELECT 1
              FROM teacher_profiles
              WHERE teacher_profiles.user_id = users.id
          )
        ON CONFLICT (user_id) DO NOTHING
        """
    )


def downgrade() -> None:
    pass
