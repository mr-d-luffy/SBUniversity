import re
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CompletionStatus,
    Course,
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


def auth(role: str, user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer dev-token-{role}-{user_id}"}


@pytest.mark.asyncio
async def test_key_request_approval_and_single_use_lifetime_unlock(
    client: AsyncClient,
    db_session: AsyncSession,
):
    student = db_session.test_student1
    course = Course(
        code="KEY-101",
        title="Key Access Course",
        teacher_id=db_session.test_teacher.id,
        is_published=True,
        price=Decimal("125.00"),
        discount_percent=20,
    )
    db_session.add(course)
    await db_session.flush()
    db_session.add(
        Enrollment(
            student_id=student.id,
            course=course,
            status=EnrollmentStatus.ACTIVE,
        )
    )
    task = Task(
        course_id=course.id,
        created_by=db_session.test_teacher.id,
        type=TaskType.ASSIGNMENT,
        title="Locked course task",
        points=10,
        verification=TaskVerification.TEACHER_APPROVAL,
        assignment_scope=TaskAssignmentScope.ALL_STUDENTS,
        status=TaskStatus.ACTIVE,
    )
    completed_task = Task(
        course_id=course.id,
        created_by=db_session.test_teacher.id,
        type=TaskType.ASSIGNMENT,
        title="Previously completed locked task",
        points=5,
        verification=TaskVerification.TEACHER_APPROVAL,
        assignment_scope=TaskAssignmentScope.ALL_STUDENTS,
        status=TaskStatus.ARCHIVED,
    )
    video_task = Task(
        course_id=course.id,
        created_by=db_session.test_teacher.id,
        type=TaskType.ASSIGNMENT,
        title="Locked video task",
        points=5,
        verification=TaskVerification.TEACHER_APPROVAL,
        resource_type=TaskResourceType.VIDEO,
        resource_url="https://youtu.be/dQw4w9WgXcQ",
        assignment_scope=TaskAssignmentScope.ALL_STUDENTS,
        status=TaskStatus.ACTIVE,
    )
    db_session.add_all([task, completed_task, video_task])
    await db_session.flush()
    db_session.add(
        TaskCompletion(
            task_id=completed_task.id,
            student_id=student.id,
            status=CompletionStatus.COMPLETED,
            points_awarded=5,
            completed_at=datetime.now(timezone.utc),
        )
    )
    await db_session.commit()

    catalog = await client.get("/student/course-catalog", headers=auth("student", "u_student1"))
    assert catalog.status_code == 200
    assert catalog.json()[0]["unlocked"] is False
    assert catalog.json()[0]["price"] == 125
    assert catalog.json()[0]["discount_percent"] == 20

    locked_enrollment = await client.post(
        f"/student/courses/{course.id}/enroll",
        headers=auth("student", "u_student1"),
    )
    assert locked_enrollment.status_code == 403
    locked_tasks = await client.get(
        f"/tasks?course_id={course.id}",
        headers=auth("student", "u_student1"),
    )
    assert locked_tasks.status_code == 404
    all_tasks = await client.get("/tasks", headers=auth("student", "u_student1"))
    assert all(
        task_response["course_id"] != str(course.id)
        for task_response in all_tasks.json()
    )
    locked_detail = await client.get(
        f"/tasks/{completed_task.id}",
        headers=auth("student", "u_student1"),
    )
    assert locked_detail.status_code == 404
    locked_submission = await client.post(
        f"/tasks/{task.id}/complete",
        json={},
        headers=auth("student", "u_student1"),
    )
    assert locked_submission.status_code == 404
    locked_video_progress = await client.post(
        f"/tasks/{video_task.id}/video-progress",
        json={"progress_percent": 10, "video_duration_seconds": 100},
        headers=auth("student", "u_student1"),
    )
    assert locked_video_progress.status_code == 404
    dashboard = await client.get(
        "/student/dashboard",
        headers=auth("student", "u_student1"),
    )
    assert all(
        task_response["course"] != course.title
        for task_response in dashboard.json()["open_tasks"]
    )

    request = await client.post(
        f"/student/courses/{course.id}/key-requests",
        headers=auth("student", "u_student1"),
    )
    assert request.status_code == 201
    request_id = request.json()["id"]
    duplicate = await client.post(
        f"/student/courses/{course.id}/key-requests",
        headers=auth("student", "u_student1"),
    )
    assert duplicate.status_code == 409

    approval = await client.post(
        f"/admin/courses/key-requests/{request_id}/approve",
        headers=auth("admin", "u_admin"),
    )
    assert approval.status_code == 200
    key = approval.json()["access_key"]
    assert re.fullmatch(r"SB-[A-Z2-9]{5}-[A-Z2-9]{5}", key)
    admin_requests = await client.get(
        "/admin/courses/key-requests",
        headers=auth("admin", "u_admin"),
    )
    assert admin_requests.json()[0]["access_key"] == key
    student_requests = await client.get(
        "/student/course-key-requests",
        headers=auth("student", "u_student1"),
    )
    assert "access_key" not in student_requests.json()[0]

    wrong_student = await client.post(
        "/student/course-key-activations",
        json={"key": key},
        headers=auth("student", "u_student2"),
    )
    assert wrong_student.status_code == 400

    activated = await client.post(
        "/student/course-key-activations",
        json={"key": key},
        headers=auth("student", "u_student1"),
    )
    assert activated.status_code == 201
    assert activated.json()["course_id"] == str(course.id)

    reused = await client.post(
        "/student/course-key-activations",
        json={"key": key},
        headers=auth("student", "u_student1"),
    )
    assert reused.status_code in {400, 409}

    catalog = await client.get("/student/course-catalog", headers=auth("student", "u_student1"))
    assert catalog.json()[0]["unlocked"] is True
    unlocked_tasks = await client.get(
        f"/tasks?course_id={course.id}",
        headers=auth("student", "u_student1"),
    )
    assert unlocked_tasks.status_code == 200
    assert {
        task_response["title"] for task_response in unlocked_tasks.json()
    } == {
        "Locked course task",
        "Previously completed locked task",
        "Locked video task",
    }


@pytest.mark.asyncio
async def test_admin_and_assigned_teacher_can_update_course_pricing(
    client: AsyncClient,
    db_session: AsyncSession,
):
    course = Course(
        code="PRICE-101",
        title="Pricing Course",
        teacher_id=db_session.test_teacher.id,
        is_published=True,
    )
    db_session.add(course)
    await db_session.commit()

    admin_update = await client.patch(
        f"/admin/courses/{course.id}",
        json={"price": "250.00", "discount_percent": 15},
        headers=auth("admin", "u_admin"),
    )
    assert admin_update.status_code == 200
    assert admin_update.json()["price"] == 250
    assert admin_update.json()["discount_percent"] == 15

    teacher_update = await client.patch(
        f"/teacher/courses/{course.id}/pricing",
        json={"price": "300.00", "discount_percent": 25},
        headers=auth("teacher", "u_teacher"),
    )
    assert teacher_update.status_code == 200
    assert teacher_update.json()["price"] == 300
    assert teacher_update.json()["discount_percent"] == 25

    invalid_discount = await client.patch(
        f"/teacher/courses/{course.id}/pricing",
        json={"price": "300.00", "discount_percent": 101},
        headers=auth("teacher", "u_teacher"),
    )
    assert invalid_discount.status_code == 422
