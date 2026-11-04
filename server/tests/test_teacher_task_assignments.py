from datetime import datetime, timedelta, timezone
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import (
    Course,
    CourseKeyRequest,
    CourseKeyRequestStatus,
    CourseTeacher,
    CourseUnlock,
    Enrollment,
    EnrollmentStatus,
    TaskVideoProgress,
    User,
    UserRole,
    UserStatus,
)


@pytest.mark.asyncio
async def test_teacher_can_create_link_task_for_selected_students(
    client: AsyncClient,
    db_session: AsyncSession,
):
    course = Course(
        code="LINK-101",
        title="Learning Resources",
        teacher_id=db_session.test_teacher.id,
        is_published=True,
    )
    db_session.add(course)
    await db_session.flush()
    db_session.add(
        CourseTeacher(
            course_id=course.id,
            teacher_id=db_session.test_teacher.id,
        )
    )
    db_session.add_all(
        [
            Enrollment(
                student_id=db_session.test_student1.id,
                course_id=course.id,
                status=EnrollmentStatus.ACTIVE,
            ),
        ]
    )
    key_requests = [
        CourseKeyRequest(
            student_id=student_id,
            course_id=course.id,
            status=CourseKeyRequestStatus.ACTIVATED,
        )
        for student_id in (
            db_session.test_student1.id,
            db_session.test_student2.id,
        )
    ]
    db_session.add_all(key_requests)
    await db_session.flush()
    db_session.add_all(
        CourseUnlock(
            student_id=request.student_id,
            course_id=course.id,
            request_id=request.id,
        )
        for request in key_requests
    )
    await db_session.commit()

    roster = await client.get(
        f"/teacher/courses/{course.id}/students",
        headers={"Authorization": "Bearer dev-token-teacher-u_teacher"},
    )
    assert roster.status_code == 200
    assert {student["id"] for student in roster.json()} == {
        str(db_session.test_student1.id),
    }
    all_courses = await client.get(
        "/teacher/task-courses",
        headers={"Authorization": "Bearer dev-token-teacher-u_teacher"},
    )
    assert course.id.hex in {
        item["id"].replace("-", "") for item in all_courses.json()
    }
    all_students = await client.get(
        "/teacher/task-students",
        headers={"Authorization": "Bearer dev-token-teacher-u_teacher"},
    )
    assert {student["id"] for student in all_students.json()} == {
        str(db_session.test_student1.id),
        str(db_session.test_student2.id),
    }

    other_teacher = User(
        clerk_user_id="u_other_teacher",
        email="other.teacher@sbuniversity.edu",
        full_name="Other Teacher",
        role=UserRole.TEACHER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(other_teacher)
    await db_session.flush()
    course.teacher_id = other_teacher.id
    await db_session.commit()

    created = await client.post(
        "/tasks",
        json={
            "course_id": str(course.id),
            "title": "Watch the introduction",
            "description": "Watch the linked video and submit a summary.",
            "points": 15,
            "resource_type": "video",
            "resource_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "assignment_scope": "selected_students",
            "target_student_ids": [str(db_session.test_student2.id)],
        },
        headers={"Authorization": "Bearer dev-token-teacher-u_teacher"},
    )
    assert created.status_code == 200, created.text
    task = created.json()
    assert task["resource_type"] == "video"
    assert task["resource_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert task["course_title"] == course.title
    assert task["assignment_scope"] == "selected_students"
    assert task["verification"] == "teacher_approval"

    unsupported_video = await client.post(
        "/tasks",
        json={
            "course_id": str(course.id),
            "title": "Unsupported video",
            "points": 5,
            "resource_type": "video",
            "resource_url": "https://example.com/intro",
        },
        headers={"Authorization": created.request.headers["Authorization"]},
    )
    assert unsupported_video.status_code == 422

    student_one_tasks = await client.get(
        "/tasks", headers={"Authorization": "Bearer dev-token-student-u_student1"}
    )
    assert student_one_tasks.status_code == 200
    assert task["id"] not in {item["id"] for item in student_one_tasks.json()}

    student_two_tasks = await client.get(
        "/tasks", headers={"Authorization": "Bearer dev-token-student-u_student2"}
    )
    assert student_two_tasks.status_code == 200
    assert task["id"] in {item["id"] for item in student_two_tasks.json()}

    all_students_task = await client.post(
        "/tasks",
        json={
            "course_id": str(course.id),
            "title": "Shared class reading",
            "points": 5,
            "resource_type": "learning_source",
            "resource_url": "https://example.com/reading",
            "assignment_scope": "all_students",
        },
        headers={"Authorization": "Bearer dev-token-teacher-u_teacher"},
    )
    assert all_students_task.status_code == 200, all_students_task.text
    shared_task_id = all_students_task.json()["id"]

    for student_token in ("dev-token-student-u_student1", "dev-token-student-u_student2"):
        shared_tasks = await client.get(
            "/tasks", headers={"Authorization": f"Bearer {student_token}"}
        )
        assert shared_tasks.status_code == 200
        shared_task_visible = shared_task_id in {item["id"] for item in shared_tasks.json()}
        dashboard = await client.get(
            "/student/dashboard",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert dashboard.status_code == 200
        dashboard_task_ids = {item["id"] for item in dashboard.json()["open_tasks"]}
        if student_token.endswith("student1"):
            assert shared_task_visible
            assert shared_task_id in dashboard_task_ids
            assert task["id"] not in dashboard_task_ids
        else:
            assert not shared_task_visible
            assert shared_task_id not in dashboard_task_ids
            assert task["id"] in dashboard_task_ids

    denied_submission = await client.post(
        f"/tasks/{task['id']}/complete",
        json={"note": "Trying to submit a task not assigned to me"},
        headers={"Authorization": "Bearer dev-token-student-u_student1"},
    )
    assert denied_submission.status_code == 404

    denied_video_progress = await client.post(
        f"/tasks/{task['id']}/video-progress",
        json={"progress_percent": 80, "video_duration_seconds": 100},
        headers={"Authorization": "Bearer dev-token-student-u_student1"},
    )
    assert denied_video_progress.status_code == 404

    insufficient_progress = await client.post(
        f"/tasks/{task['id']}/video-progress",
        json={"progress_percent": 79, "video_duration_seconds": 100},
        headers={"Authorization": "Bearer dev-token-student-u_student2"},
    )
    assert insufficient_progress.status_code == 200
    assert insufficient_progress.json()["progress_percent"] == 0

    blocked_submission = await client.post(
        f"/tasks/{task['id']}/complete",
        json={"note": "I watched the lesson"},
        headers={"Authorization": "Bearer dev-token-student-u_student2"},
    )
    assert blocked_submission.status_code == 400

    progress_record = await db_session.get(
        TaskVideoProgress,
        (uuid.UUID(task["id"]), db_session.test_student2.id),
    )
    assert progress_record is not None
    progress_record.updated_at = datetime.now(timezone.utc) - timedelta(seconds=40)
    await db_session.commit()
    watched_progress = await client.post(
        f"/tasks/{task['id']}/video-progress",
        json={"progress_percent": 79, "video_duration_seconds": 100},
        headers={"Authorization": "Bearer dev-token-student-u_student2"},
    )
    assert watched_progress.status_code == 200
    assert watched_progress.json()["progress_percent"] == 79

    progress_record.updated_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.commit()
    enough_progress = await client.post(
        f"/tasks/{task['id']}/video-progress",
        json={"progress_percent": 80, "video_duration_seconds": 100},
        headers={"Authorization": "Bearer dev-token-student-u_student2"},
    )
    assert enough_progress.status_code == 200
    assert enough_progress.json()["progress_percent"] == 80

    lower_progress = await client.post(
        f"/tasks/{task['id']}/video-progress",
        json={"progress_percent": 40, "video_duration_seconds": 100},
        headers={"Authorization": "Bearer dev-token-student-u_student2"},
    )
    assert lower_progress.status_code == 200
    assert lower_progress.json()["progress_percent"] == 80
    task_list_with_progress = await client.get(
        "/tasks",
        headers={"Authorization": student_two_tasks.request.headers["Authorization"]},
    )
    assert task_list_with_progress.status_code == 200
    saved_task = next(item for item in task_list_with_progress.json() if item["id"] == task["id"])
    assert saved_task["my_video_progress"] == 80

    allowed_submission = await client.post(
        f"/tasks/{task['id']}/complete",
        json={"note": "I watched the lesson"},
        headers={"Authorization": "Bearer dev-token-student-u_student2"},
    )
    assert allowed_submission.status_code == 200
    completion = allowed_submission.json()
    assert completion["status"] == "pending_review"
    assert completion["points_awarded"] == 0
    assert completion["completed_at"] is None

    student_points = await client.get(
        "/student/points",
        headers={"Authorization": "Bearer dev-token-student-u_student2"},
    )
    assert student_points.status_code == 200
    assert student_points.json()["total_points"] == 0

    reviews = await client.get(
        "/tasks/reviews",
        headers={"Authorization": "Bearer dev-token-teacher-u_teacher"},
    )
    assert reviews.status_code == 200
    review = next(item for item in reviews.json() if item["id"] == completion["completion_id"])
    assert review["points_awarded"] == 0
    assert review["points_available"] == 15

    approved = await client.post(
        f"/tasks/completions/{completion['completion_id']}/approve",
        json={"review_note": "Approved task completion."},
        headers={"Authorization": "Bearer dev-token-teacher-u_teacher"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "completed"
    assert approved.json()["points_awarded"] == 15

    ranking = await client.get(
        "/ranking/top",
        headers={"Authorization": "Bearer dev-token-student-u_student2"},
    )
    assert ranking.status_code == 200
    assert any(
        item["student_id"] == str(db_session.test_student2.id)
        and item["points"] == 15
        for item in ranking.json()["items"]
    )
    student_points = await client.get(
        "/student/points",
        headers={"Authorization": "Bearer dev-token-student-u_student2"},
    )
    assert student_points.status_code == 200
    assert student_points.json()["total_points"] == 15


@pytest.mark.asyncio
async def test_selected_task_allows_any_active_student(
    client: AsyncClient,
    db_session: AsyncSession,
):
    course = Course(
        code="LINK-102",
        title="Another Learning Resource",
        teacher_id=db_session.test_teacher.id,
        is_published=True,
    )
    db_session.add(course)
    await db_session.commit()

    response = await client.post(
        "/tasks",
        json={
            "course_id": str(course.id),
            "title": "Not enrolled",
            "points": 5,
            "resource_type": "learning_source",
            "resource_url": "https://example.com/reading",
            "assignment_scope": "selected_students",
            "target_student_ids": [str(db_session.test_student1.id)],
        },
        headers={"Authorization": "Bearer dev-token-teacher-u_teacher"},
    )
    assert response.status_code == 200, response.text
