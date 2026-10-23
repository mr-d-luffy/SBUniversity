import pytest
import uuid
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Course, Enrollment, EnrollmentStatus, User, UserRole, UserStatus
from app.db.models.exam import Exam, ExamStatus
from app.db.models.task import Task, TaskStatus, TaskType, TaskVerification


ADMIN_AUTH = {"Authorization": "Bearer dev-token-admin-u_admin"}


@pytest.mark.asyncio
async def test_admin_creates_published_course_and_enrolls_all_active_students(
    client: AsyncClient,
    db_session: AsyncSession,
):
    suspended_student = User(
        clerk_user_id="u_suspended_student",
        email="suspended@sbuniversity.edu",
        full_name="Suspended Student",
        role=UserRole.STUDENT,
        status=UserStatus.SUSPENDED,
    )
    db_session.add(suspended_student)
    await db_session.commit()

    response = await client.post(
        "/admin/courses",
        json={
            "code": "OU-2026-01",
            "title": "OpenUniversity Course",
            "description": "An open course for all active students.",
        },
        headers={"Authorization": "Bearer dev-token-admin-u_admin"},
    )
    assert response.status_code == 201, response.text
    course = response.json()
    assert course["code"] == "OU-2026-01"
    assert course["title"] == "OpenUniversity Course"
    assert course["is_published"] is True
    assert course["enrolled_students"] == 2

    enrollments = (
        await db_session.execute(
            select(Enrollment).where(
                Enrollment.course_id == uuid.UUID(course["id"])
            )
        )
    ).scalars().all()
    assert {enrollment.student_id for enrollment in enrollments} == {
        db_session.test_student1.id,
        db_session.test_student2.id,
    }
    assert all(enrollment.status == EnrollmentStatus.ACTIVE for enrollment in enrollments)

    courses_response = await client.get(
        "/admin/courses",
        headers={"Authorization": "Bearer dev-token-admin-u_admin"},
    )
    assert courses_response.status_code == 200
    assert any(
        item["id"] == course["id"] and item["enrolled_students"] == 2
        for item in courses_response.json()
    )


@pytest.mark.asyncio
async def test_admin_can_create_course_without_enrolling_students(
    client: AsyncClient,
):
    response = await client.post(
        "/admin/courses",
        json={
            "code": "OU-EMPTY",
            "title": "Optional enrollment",
            "enroll_all_active_students": False,
        },
        headers={"Authorization": "Bearer dev-token-admin-u_admin"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["enrolled_students"] == 0


@pytest.mark.asyncio
async def test_teacher_cannot_create_admin_course(client: AsyncClient):
    response = await client.post(
        "/admin/courses",
        json={"code": "OU-NOPE", "title": "Forbidden course"},
        headers={"Authorization": "Bearer dev-token-teacher-u_teacher"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_assign_specific_teachers_and_students(
    client: AsyncClient,
    db_session: AsyncSession,
):
    second_teacher = User(
        clerk_user_id="u_teacher_two",
        email="teacher2@sbuniversity.edu",
        full_name="Second Teacher",
        role=UserRole.TEACHER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(second_teacher)
    await db_session.commit()

    response = await client.post(
        "/admin/courses",
        json={
            "code": "SBU-SELECTED",
            "title": "Selected roster",
            "teacher_ids": [str(db_session.test_teacher.id), str(second_teacher.id)],
            "student_ids": [str(db_session.test_student1.id)],
            "enroll_all_active_students": False,
        },
        headers=ADMIN_AUTH,
    )
    assert response.status_code == 201, response.text
    course = response.json()
    assert set(course["teacher_ids"]) == {
        str(db_session.test_teacher.id),
        str(second_teacher.id),
    }
    assert course["student_ids"] == [str(db_session.test_student1.id)]
    assert course["enrolled_students"] == 1

    teacher_chat_courses = await client.get(
        "/whiteboard/courses",
        headers={"Authorization": "Bearer dev-token-teacher-u_teacher_two"},
    )
    assert teacher_chat_courses.status_code == 200, teacher_chat_courses.text
    assert any(item["id"] == course["id"] for item in teacher_chat_courses.json())

    update = await client.patch(
        f"/admin/courses/{course['id']}",
        json={
            "title": "Updated roster",
            "student_ids": [
                str(db_session.test_student1.id),
                str(db_session.test_student2.id),
            ],
            "enroll_all_active_students": False,
        },
        headers=ADMIN_AUTH,
    )
    assert update.status_code == 200, update.text
    assert update.json()["title"] == "Updated roster"
    assert set(update.json()["student_ids"]) == {
        str(db_session.test_student1.id),
        str(db_session.test_student2.id),
    }


@pytest.mark.asyncio
async def test_admin_can_delete_course_and_its_enrollments(
    client: AsyncClient,
    db_session: AsyncSession,
):
    created = await client.post(
        "/admin/courses",
        json={
            "code": "SBU-DELETE",
            "title": "Course to delete",
            "teacher_ids": [str(db_session.test_teacher.id)],
            "student_ids": [str(db_session.test_student1.id)],
            "enroll_all_active_students": False,
        },
        headers=ADMIN_AUTH,
    )
    assert created.status_code == 201, created.text
    course_id = uuid.UUID(created.json()["id"])
    exam = Exam(
        course_id=course_id,
        created_by=db_session.test_teacher.id,
        title="Course exam",
        duration_minutes=30,
        start_at=datetime.now(timezone.utc),
        end_at=datetime.now(timezone.utc) + timedelta(hours=1),
        status=ExamStatus.DRAFT,
    )
    db_session.add(exam)
    await db_session.flush()
    task = Task(
        course_id=course_id,
        created_by=db_session.test_teacher.id,
        type=TaskType.EXAM,
        exam_id=exam.id,
        title="Exam points",
        points=10,
        verification=TaskVerification.AUTO,
        status=TaskStatus.ACTIVE,
    )
    db_session.add(task)
    await db_session.commit()

    deleted = await client.delete(
        f"/admin/courses/{course_id}",
        headers=ADMIN_AUTH,
    )
    assert deleted.status_code == 204
    assert await db_session.get(Course, course_id) is None
    assert await db_session.get(Exam, exam.id) is None
    assert await db_session.get(Task, task.id) is None
    assert (
        await db_session.scalar(
            select(Enrollment.id).where(Enrollment.course_id == course_id)
        )
        is None
    )


@pytest.mark.asyncio
async def test_admin_can_assign_existing_course_to_active_teacher_and_teacher_sees_it(
    client: AsyncClient,
    db_session: AsyncSession,
):
    course = Course(
        code="UNASSIGNED-01",
        title="Previously unassigned course",
        teacher_id=db_session.test_admin.id,
        is_published=True,
    )
    db_session.add(course)
    await db_session.commit()

    teachers = await client.get(
        "/admin/courses/teachers",
        headers=ADMIN_AUTH,
    )
    assert teachers.status_code == 200
    assert any(
        teacher["id"] == str(db_session.test_teacher.id)
        for teacher in teachers.json()
    )

    assigned = await client.patch(
        f"/admin/courses/{course.id}/teacher",
        json={"teacher_id": str(db_session.test_teacher.id)},
        headers=ADMIN_AUTH,
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["teacher_id"] == str(db_session.test_teacher.id)

    teacher_courses = await client.get(
        "/whiteboard/courses",
        headers={"Authorization": "Bearer dev-token-teacher-u_teacher"},
    )
    assert teacher_courses.status_code == 200
    assert any(item["id"] == str(course.id) for item in teacher_courses.json())
    live_class = await client.post(
        f"/whiteboard/courses/{course.id}/sessions",
        headers={"Authorization": "Bearer dev-token-teacher-u_teacher"},
    )
    assert live_class.status_code == 201, live_class.text

    rejected = await client.patch(
        f"/admin/courses/{course.id}/teacher",
        json={"teacher_id": str(db_session.test_admin.id)},
        headers=ADMIN_AUTH,
    )
    assert rejected.status_code == 422
