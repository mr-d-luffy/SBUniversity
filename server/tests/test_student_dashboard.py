from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CompletionStatus,
    Course,
    CourseKeyRequest,
    CourseKeyRequestStatus,
    CourseUnlock,
    Enrollment,
    EnrollmentStatus,
    Task,
    TaskAssignmentScope,
    TaskCompletion,
    TaskStatus,
    TaskType,
    TaskVerification,
)


@pytest.mark.asyncio
async def test_dashboard_batches_task_completion_status_lookups(
    client: AsyncClient,
    db_session: AsyncSession,
):
    course = Course(
        code="DASHBOARD-101",
        title="Dashboard Testing",
        teacher_id=db_session.test_teacher.id,
        is_published=True,
    )
    db_session.add(course)
    await db_session.flush()
    db_session.add(
        Enrollment(
            student_id=db_session.test_student1.id,
            course_id=course.id,
            status=EnrollmentStatus.ACTIVE,
        )
    )
    key_request = CourseKeyRequest(
        student_id=db_session.test_student1.id,
        course_id=course.id,
        status=CourseKeyRequestStatus.ACTIVATED,
    )
    db_session.add(key_request)
    await db_session.flush()
    db_session.add(
        CourseUnlock(
            student_id=db_session.test_student1.id,
            course_id=course.id,
            request_id=key_request.id,
        )
    )

    now = datetime.now(timezone.utc)
    tasks = [
        Task(
            course_id=course.id,
            type=TaskType.ASSIGNMENT,
            title=f"Dashboard task {index}",
            points=10,
            verification=TaskVerification.TEACHER_APPROVAL,
            assignment_scope=TaskAssignmentScope.ALL_STUDENTS,
            status=TaskStatus.ACTIVE,
            created_at=now + timedelta(seconds=index),
        )
        for index in range(6)
    ]
    db_session.add_all(tasks)
    await db_session.flush()

    statuses = (
        CompletionStatus.PENDING_REVIEW,
        CompletionStatus.COMPLETED,
        CompletionStatus.REJECTED,
        CompletionStatus.REVOKED,
    )
    db_session.add_all(
        [
            TaskCompletion(
                task_id=task.id,
                student_id=db_session.test_student1.id,
                status=status,
                completed_at=now if status == CompletionStatus.COMPLETED else None,
            )
            for task, status in zip(tasks, statuses)
        ]
    )
    await db_session.commit()

    task_completion_status_queries = []

    def record_completion_lookups(
        _conn, _cursor, statement, _parameters, _context, _executemany
    ):
        lowered_statement = statement.lower()
        where_clause = lowered_statement.partition("where")[2]
        if (
            "from task_completions" in lowered_statement
            and "task_completions.task_id" in where_clause
        ):
            task_completion_status_queries.append(statement)

    sync_engine = db_session.bind.sync_engine
    event.listen(sync_engine, "before_cursor_execute", record_completion_lookups)
    try:
        response = await client.get(
            "/student/dashboard",
            headers={"Authorization": "Bearer dev-token-student-u_student1"},
        )
    finally:
        event.remove(sync_engine, "before_cursor_execute", record_completion_lookups)

    assert response.status_code == 200, response.text
    task_statuses = {
        task["title"]: task["status"] for task in response.json()["open_tasks"]
    }
    assert task_statuses == {
        "Dashboard task 0": "pending_review",
        "Dashboard task 1": "completed",
        "Dashboard task 2": "rejected",
        "Dashboard task 3": "revoked",
        "Dashboard task 4": "open",
        "Dashboard task 5": "open",
    }
    assert len(task_completion_status_queries) == 1
