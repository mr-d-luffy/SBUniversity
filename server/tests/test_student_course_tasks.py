from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
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
    TaskResourceType,
    TaskStatus,
    TaskType,
    TaskVerification,
)


async def unlock_course(db_session, student, course):
    request = CourseKeyRequest(
        student_id=student.id,
        course_id=course.id,
        status=CourseKeyRequestStatus.ACTIVATED,
    )
    db_session.add(request)
    await db_session.flush()
    db_session.add(
        CourseUnlock(
            student_id=student.id,
            course_id=course.id,
            request_id=request.id,
        )
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
    await unlock_course(db_session, student, course)
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


@pytest.mark.asyncio
async def test_student_keeps_access_to_own_completed_archived_course_task(
    client: AsyncClient,
    db_session: AsyncSession,
):
    student = db_session.test_student1
    course = Course(
        code="TASK-HISTORY",
        title="Task History",
        teacher_id=db_session.test_teacher.id,
        is_published=True,
    )
    db_session.add(course)
    await db_session.flush()
    db_session.add(
        Enrollment(
            student_id=student.id,
            course_id=course.id,
            status=EnrollmentStatus.DROPPED,
        )
    )
    await unlock_course(db_session, student, course)
    completed_task = Task(
        course_id=course.id,
        created_by=db_session.test_teacher.id,
        type=TaskType.ASSIGNMENT,
        title="Completed video task",
        points=12,
        verification=TaskVerification.TEACHER_APPROVAL,
        resource_type=TaskResourceType.VIDEO,
        resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        assignment_scope=TaskAssignmentScope.ALL_STUDENTS,
        status=TaskStatus.ARCHIVED,
    )
    uncompleted_task = Task(
        course_id=course.id,
        created_by=db_session.test_teacher.id,
        type=TaskType.ASSIGNMENT,
        title="Archived task without completion",
        points=5,
        verification=TaskVerification.TEACHER_APPROVAL,
        assignment_scope=TaskAssignmentScope.ALL_STUDENTS,
        status=TaskStatus.ARCHIVED,
    )
    db_session.add_all([completed_task, uncompleted_task])
    await db_session.flush()
    completed_at = datetime.now(timezone.utc)
    db_session.add(
        TaskCompletion(
            task_id=completed_task.id,
            student_id=student.id,
            status=CompletionStatus.COMPLETED,
            points_awarded=12,
            submitted_at=completed_at,
            completed_at=completed_at,
        )
    )
    await db_session.commit()

    headers = {"Authorization": "Bearer dev-token-student-u_student1"}
    course_tasks = await client.get(
        f"/tasks?course_id={course.id}",
        headers=headers,
    )
    assert course_tasks.status_code == 200
    assert [task["id"] for task in course_tasks.json()] == [str(completed_task.id)]
    assert course_tasks.json()[0]["resource_url"] == completed_task.resource_url
    assert course_tasks.json()[0]["my_status"] == CompletionStatus.COMPLETED.value

    task_detail = await client.get(f"/tasks/{completed_task.id}", headers=headers)
    assert task_detail.status_code == 200
    assert task_detail.json()["resource_url"] == completed_task.resource_url

    another_student_detail = await client.get(
        f"/tasks/{completed_task.id}",
        headers={"Authorization": "Bearer dev-token-student-u_student2"},
    )
    assert another_student_detail.status_code == 404
