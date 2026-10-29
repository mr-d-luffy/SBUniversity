import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Course,
    Enrollment,
    EnrollmentStatus,
    Task,
    TaskAssignmentScope,
    TaskStatus,
    TaskType,
    TaskVerification,
)


@pytest.mark.asyncio
async def test_student_fetches_all_active_tasks_for_enrolled_course(
    client: AsyncClient,
    db_session: AsyncSession,
):
    student = db_session.test_student1
    teacher = db_session.test_teacher
    course = Course(
        code="TASKS-101",
        title="Course Tasks",
        teacher_id=teacher.id,
        is_published=True,
    )
    other_course = Course(
        code="TASKS-102",
        title="Another Course",
        teacher_id=teacher.id,
        is_published=True,
    )
    db_session.add_all([course, other_course])
    await db_session.flush()
    db_session.add(
        Enrollment(
            student_id=student.id,
            course_id=course.id,
            status=EnrollmentStatus.ACTIVE,
        )
    )
    expected_tasks = [
        Task(
            course_id=course.id,
            created_by=teacher.id,
            type=TaskType.ASSIGNMENT,
            title=title,
            points=10,
            verification=TaskVerification.TEACHER_APPROVAL,
            assignment_scope=TaskAssignmentScope.ALL_STUDENTS,
            status=TaskStatus.ACTIVE,
        )
        for title in ("First task", "Second task")
    ]
    db_session.add_all(
        [
            *expected_tasks,
            Task(
                course_id=course.id,
                created_by=teacher.id,
                type=TaskType.ASSIGNMENT,
                title="Archived task",
                points=10,
                verification=TaskVerification.TEACHER_APPROVAL,
                assignment_scope=TaskAssignmentScope.ALL_STUDENTS,
                status=TaskStatus.ARCHIVED,
            ),
            Task(
                course_id=other_course.id,
                created_by=teacher.id,
                type=TaskType.ASSIGNMENT,
                title="Other course task",
                points=10,
                verification=TaskVerification.TEACHER_APPROVAL,
                assignment_scope=TaskAssignmentScope.ALL_STUDENTS,
                status=TaskStatus.ACTIVE,
            ),
        ]
    )
    await db_session.commit()

    response = await client.get(
        f"/tasks?course_id={course.id}",
        headers={"Authorization": "Bearer dev-token-student-u_student1"},
    )

    assert response.status_code == 200
    assert {task["title"] for task in response.json()} == {
        "First task",
        "Second task",
    }


@pytest.mark.asyncio
async def test_student_cannot_fetch_tasks_for_unenrolled_course(
    client: AsyncClient,
    db_session: AsyncSession,
):
    course = Course(
        code="NOT-ENROLLED",
        title="Not Enrolled",
        teacher_id=db_session.test_teacher.id,
        is_published=True,
    )
    db_session.add(course)
    await db_session.commit()

    response = await client.get(
        f"/tasks?course_id={course.id}",
        headers={"Authorization": "Bearer dev-token-student-u_student1"},
    )

    assert response.status_code == 404
