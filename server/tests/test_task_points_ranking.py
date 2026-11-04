from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import (
    Course,
    CourseKeyRequest,
    CourseKeyRequestStatus,
    CourseUnlock,
    Enrollment,
    EnrollmentStatus,
)
from app.db.models.task import CompletionStatus, Task, TaskCompletion, TaskType, TaskVerification


@pytest.mark.asyncio
async def test_assignment_task_points_and_ranking_flow(client: AsyncClient, db_session: AsyncSession):
    teacher_id = db_session.test_teacher.id
    student1_id = db_session.test_student1.id
    student2_id = db_session.test_student2.id

    # Course & Enrollments
    course = Course(code="AI-TEST", title="Machine Learning Lab", teacher_id=teacher_id, is_published=True)
    db_session.add(course)
    await db_session.flush()

    db_session.add(Enrollment(student_id=student1_id, course_id=course.id, status=EnrollmentStatus.ACTIVE))
    db_session.add(Enrollment(student_id=student2_id, course_id=course.id, status=EnrollmentStatus.ACTIVE))
    requests = [
        CourseKeyRequest(
            student_id=student_id,
            course_id=course.id,
            status=CourseKeyRequestStatus.ACTIVATED,
        )
        for student_id in (student1_id, student2_id)
    ]
    db_session.add_all(requests)
    await db_session.flush()
    db_session.add_all(
        CourseUnlock(
            student_id=request.student_id,
            course_id=course.id,
            request_id=request.id,
        )
        for request in requests
    )
    await db_session.commit()

    # 1. Teacher creates assignment task with 60 points
    t_payload = {
        "course_id": str(course.id),
        "title": "Neural Network PyTorch Assignment",
        "description": "Implement backpropagation from scratch",
        "points": 60,
    }
    resp = await client.post("/tasks", json=t_payload, headers={"Authorization": "Bearer dev-token-teacher-u_teacher"})
    assert resp.status_code == 200
    task_id = resp.json()["id"]

    # 2. Student 1 submits assignment
    resp = await client.post(
        f"/tasks/{task_id}/complete",
        json={"note": "Repository attached", "url": "https://github.com/student1/pytorch-nn"},
        headers={"Authorization": "Bearer dev-token-student-u_student1"},
    )
    assert resp.status_code == 200
    completion_id = resp.json()["completion_id"]
    assert resp.json()["status"] == "pending_review"

    # 3. Teacher checks reviews
    resp = await client.get("/tasks/reviews", headers={"Authorization": "Bearer dev-token-teacher-u_teacher"})
    assert resp.status_code == 200
    reviews = resp.json()
    assert any(r["id"] == completion_id for r in reviews)

    # 4. Teacher approves completion -> points auto-awarded!
    resp = await client.post(
        f"/tasks/completions/{completion_id}/approve",
        json={"review_note": "Excellent implementation of backprop."},
        headers={"Authorization": "Bearer dev-token-teacher-u_teacher"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["points_awarded"] == 60

    # 5. Check Live Ranking endpoint
    resp = await client.get("/ranking/top", headers={"Authorization": "Bearer dev-token-student-u_student1"})
    assert resp.status_code == 200
    lb = resp.json()
    assert len(lb["items"]) >= 1
    top_student = lb["items"][0]
    assert top_student["student_id"] == str(student1_id)
    assert top_student["points"] == 60

    # 6. Admin revokes completion
    resp = await client.post(
        f"/admin/progress/tasks/completions/{completion_id}/revoke?reason=Test+Revoke",
        headers={"Authorization": "Bearer dev-token-admin-u_admin"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "revoked"
    assert resp.json()["points_awarded"] == 0

    # 7. Check student points after revoke -> points 0
    resp = await client.get("/student/points", headers={"Authorization": "Bearer dev-token-student-u_student1"})
    assert resp.status_code == 200
    assert resp.json()["total_points"] == 0


@pytest.mark.asyncio
async def test_course_my_rank_uses_course_points_and_requires_course_id(
    client: AsyncClient,
    db_session: AsyncSession,
):
    teacher_id = db_session.test_teacher.id
    student1_id = db_session.test_student1.id
    student2_id = db_session.test_student2.id
    course = Course(
        code="RANK-COURSE",
        title="Course Ranking",
        teacher_id=teacher_id,
        is_published=True,
    )
    other_course = Course(
        code="RANK-OTHER",
        title="Other Course",
        teacher_id=teacher_id,
        is_published=True,
    )
    db_session.add_all([course, other_course])
    await db_session.flush()

    request = CourseKeyRequest(
        student_id=student1_id,
        course_id=course.id,
        status=CourseKeyRequestStatus.ACTIVATED,
    )
    db_session.add(request)
    await db_session.flush()
    db_session.add(
        CourseUnlock(
            student_id=student1_id,
            course_id=course.id,
            request_id=request.id,
        )
    )

    tasks = [
        Task(
            course_id=course.id,
            type=TaskType.ASSIGNMENT,
            title="Student one course task",
            points=10,
            verification=TaskVerification.AUTO,
        ),
        Task(
            course_id=course.id,
            type=TaskType.ASSIGNMENT,
            title="Student two course task",
            points=25,
            verification=TaskVerification.AUTO,
        ),
        Task(
            course_id=other_course.id,
            type=TaskType.ASSIGNMENT,
            title="Student one other task",
            points=70,
            verification=TaskVerification.AUTO,
        ),
    ]
    db_session.add_all(tasks)
    await db_session.flush()
    completed_at = datetime.now(timezone.utc)
    db_session.add_all(
        [
            TaskCompletion(
                task_id=tasks[0].id,
                student_id=student1_id,
                status=CompletionStatus.COMPLETED,
                points_awarded=10,
                completed_at=completed_at,
            ),
            TaskCompletion(
                task_id=tasks[1].id,
                student_id=student2_id,
                status=CompletionStatus.COMPLETED,
                points_awarded=25,
                completed_at=completed_at,
            ),
            TaskCompletion(
                task_id=tasks[2].id,
                student_id=student1_id,
                status=CompletionStatus.COMPLETED,
                points_awarded=70,
                completed_at=completed_at,
            ),
        ]
    )
    await db_session.commit()

    response = await client.get(
        f"/ranking/me?scope=course&course_id={course.id}",
        headers={"Authorization": "Bearer dev-token-student-u_student1"},
    )
    assert response.status_code == 200
    assert response.json()["rank"] == 2
    assert response.json()["points"] == 10
    assert response.json()["tasks_completed"] == 1

    top_response = await client.get(
        f"/ranking/top?scope=course&course_id={course.id}",
        headers={"Authorization": "Bearer dev-token-student-u_student1"},
    )
    assert top_response.status_code == 200
    assert top_response.json()["items"][0]["student_id"] == str(student2_id)

    refresh_task = Task(
        course_id=course.id,
        type=TaskType.ASSIGNMENT,
        title="Student one additional course task",
        points=20,
        verification=TaskVerification.AUTO,
    )
    db_session.add(refresh_task)
    await db_session.flush()
    db_session.add(
        TaskCompletion(
            task_id=refresh_task.id,
            student_id=student1_id,
            status=CompletionStatus.COMPLETED,
            points_awarded=20,
            completed_at=completed_at,
        )
    )
    await db_session.commit()
    refreshed_top = await client.get(
        f"/ranking/top?scope=course&course_id={course.id}",
        headers={"Authorization": "Bearer dev-token-student-u_student1"},
    )
    assert refreshed_top.status_code == 200
    assert refreshed_top.json()["items"][0]["student_id"] == str(student1_id)
    assert refreshed_top.json()["items"][0]["points"] == 30

    invalid_scope = await client.get(
        "/ranking/me?scope=course",
        headers={"Authorization": "Bearer dev-token-student-u_student1"},
    )
    assert invalid_scope.status_code == 422
