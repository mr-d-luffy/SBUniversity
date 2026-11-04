from datetime import datetime, timezone

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.db.models import (
    CompletionStatus,
    Course,
    Task,
    TaskAssignmentScope,
    TaskCompletion,
    TaskStatus,
    TaskType,
    TaskVerification,
    User,
    UserRole,
    UserStatus,
)
from app.repositories.user_repository import UserRepository
from app.services.analytics_service import AnalyticsService
from app.services.ranking_service import RankingService


@pytest.mark.asyncio
async def test_analytics_query_counts_are_bounded_by_report_type(
    db_session: AsyncSession,
):
    for index in range(20):
        db_session.add(
            User(
                clerk_user_id=f"u_extra_student_{index}",
                email=f"extra_student_{index}@sbuniversity.edu",
                full_name=f"Extra Student {index}",
                role=UserRole.STUDENT,
                status=UserStatus.ACTIVE,
            )
        )
    await db_session.flush()

    statement_count = 0

    def count_statement(*_args):
        nonlocal statement_count
        statement_count += 1

    event.listen(db_session.bind.sync_engine, "before_cursor_execute", count_statement)
    try:
        service = AnalyticsService(db_session)

        statement_count = 0
        overview = await service.get_overview_analytics()
        assert statement_count == 1
        assert overview.total_students == 22

        statement_count = 0
        teachers = await service.get_teacher_analytics()
        assert statement_count <= 6
        assert len(teachers) == 1

        statement_count = 0
        students = await service.get_student_analytics(limit=50)
        assert statement_count <= 6
        assert len(students) == 22

        statement_count = 0
        await service.get_public_stats()
        assert statement_count == 1
    finally:
        event.remove(db_session.bind.sync_engine, "before_cursor_execute", count_statement)


@pytest.mark.asyncio
async def test_leaderboard_hydrates_cached_students_with_one_query(
    db_session: AsyncSession,
):
    course = Course(
        code="RANK-TEST",
        title="Ranking Test",
        teacher_id=db_session.test_teacher.id,
    )
    task = Task(
        course=course,
        created_by=db_session.test_teacher.id,
        type=TaskType.ASSIGNMENT,
        title="Completed task",
        points=80,
        verification=TaskVerification.TEACHER_APPROVAL,
        assignment_scope=TaskAssignmentScope.ALL_STUDENTS,
        status=TaskStatus.ACTIVE,
    )
    completed_at = datetime.now(timezone.utc)
    db_session.add_all(
        [
            task,
            TaskCompletion(
                task=task,
                student_id=db_session.test_student1.id,
                status=CompletionStatus.COMPLETED,
                points_awarded=80,
                completed_at=completed_at,
            ),
            TaskCompletion(
                task=task,
                student_id=db_session.test_student2.id,
                status=CompletionStatus.COMPLETED,
                points_awarded=40,
                completed_at=completed_at,
            ),
        ]
    )
    await db_session.flush()

    redis = await get_redis_client()
    await redis.zadd(
        "lb:overall",
        {
            str(db_session.test_student1.id): 80,
            str(db_session.test_student2.id): 40,
        },
    )
    statement_count = 0

    def count_statement(*_args):
        nonlocal statement_count
        statement_count += 1

    event.listen(
        db_session.bind.sync_engine,
        "before_cursor_execute",
        count_statement,
    )
    try:
        response = await RankingService(db_session).get_top_students(limit=2)
    finally:
        event.remove(
            db_session.bind.sync_engine,
            "before_cursor_execute",
            count_statement,
        )

    assert statement_count == 1
    assert [item.points for item in response.items] == [80, 40]
    assert [item.tasks_completed for item in response.items] == [1, 1]


@pytest.mark.asyncio
async def test_student_code_generation_reads_only_codes_for_requested_year(
    db_session: AsyncSession,
):
    statement_count = 0

    def count_statement(*_args):
        nonlocal statement_count
        statement_count += 1

    event.listen(
        db_session.bind.sync_engine,
        "before_cursor_execute",
        count_statement,
    )
    try:
        student_code = await UserRepository(db_session).next_student_code(2026)
    finally:
        event.remove(
            db_session.bind.sync_engine,
            "before_cursor_execute",
            count_statement,
        )

    assert statement_count == 1
    assert student_code == "SBU-2026-0003"
