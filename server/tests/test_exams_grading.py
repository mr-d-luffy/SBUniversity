from datetime import datetime, timedelta, timezone
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Course, Enrollment, EnrollmentStatus, Task


@pytest.mark.asyncio
async def test_exam_lifecycle_grading_and_task_points(client: AsyncClient, db_session: AsyncSession):
    now = datetime.now(timezone.utc)
    teacher_id = db_session.test_teacher.id
    student1_id = db_session.test_student1.id

    # 1. Create course & enrollment
    course = Course(
        code="CS-TEST",
        title="Test Computer Science",
        teacher_id=teacher_id,
        is_published=True,
    )
    db_session.add(course)
    await db_session.flush()

    enrollment = Enrollment(
        student_id=student1_id,
        course_id=course.id,
        status=EnrollmentStatus.ACTIVE,
    )
    db_session.add(enrollment)
    await db_session.commit()

    # 2. Teacher creates exam
    exam_payload = {
        "course_id": str(course.id),
        "title": "Algorithms Midterm",
        "instructions": "Attempt all questions",
        "duration_minutes": 30,
        "pass_marks": 0.0,
        "negative_marking": 0.0,
        "max_attempts": 1,
        "start_at": (now - timedelta(hours=1)).isoformat(),
        "end_at": (now + timedelta(hours=5)).isoformat(),
    }
    resp = await client.post("/exams", json=exam_payload, headers={"Authorization": "Bearer dev-token-teacher-u_teacher"})
    assert resp.status_code == 200
    teacher_auth = resp.request.headers["Authorization"]
    exam_data = resp.json()
    exam_id = exam_data["id"]

    # 3. Teacher adds question
    q_payload = {
        "text": "What is the time complexity of binary search?",
        "marks": 10.0,
        "position": 1,
        "explanation": "Binary search divides the search interval in half each time.",
        "options": [
            {"text": "O(log n)", "is_correct": True, "position": 1},
            {"text": "O(n)", "is_correct": False, "position": 2},
            {"text": "O(n^2)", "is_correct": False, "position": 3},
        ],
    }
    resp = await client.post(f"/exams/{exam_id}/questions", json=q_payload, headers={"Authorization": "Bearer dev-token-teacher-u_teacher"})
    assert resp.status_code == 200
    q_data = resp.json()
    opt_correct_id = next(o["id"] for o in q_data["options"] if o["text"] == "O(log n)")

    resp = await client.patch(
        f"/exams/{exam_id}",
        json={"pass_marks": 5.0},
        headers={"Authorization": resp.request.headers["Authorization"]},
    )
    assert resp.status_code == 200
    assert resp.json()["pass_marks"] == 5.0

    # 4. Teacher publishes exam with 50 Task Points
    resp = await client.post(f"/exams/{exam_id}/publish", json={"task_points": 50}, headers={"Authorization": "Bearer dev-token-teacher-u_teacher"})
    assert resp.status_code == 200

    # 5. Student starts attempt
    resp = await client.post(f"/exams/{exam_id}/attempts", headers={"Authorization": "Bearer dev-token-student-u_student1"})
    assert resp.status_code == 200
    attempt_data = resp.json()
    attempt_id = attempt_data["attempt_id"]
    # Check that is_correct is NOT leaked to student
    for q in attempt_data["questions"]:
        for opt in q["options"]:
            assert opt.get("is_correct") is None

    edit_started_exam = await client.patch(
        f"/exams/{exam_id}",
        json={
            "questions": [
                {
                    "text": "Changed after attempt start",
                    "marks": 10,
                    "position": 1,
                    "options": [
                        {"text": "Correct", "is_correct": True, "position": 1},
                        {"text": "Incorrect", "is_correct": False, "position": 2},
                    ],
                },
            ],
        },
        headers={"Authorization": teacher_auth},
    )
    assert edit_started_exam.status_code == 409

    # 6. Student autosaves correct answer
    resp = await client.put(
        f"/attempts/{attempt_id}/answers/{q_data['id']}",
        json={"selected_option_id": opt_correct_id},
        headers={"Authorization": "Bearer dev-token-student-u_student1"},
    )
    assert resp.status_code == 200
    assert resp.json()["saved"] is True

    # 7. Student submits attempt
    resp = await client.post(f"/attempts/{attempt_id}/submit", headers={"Authorization": "Bearer dev-token-student-u_student1"})
    assert resp.status_code == 200
    submit_res = resp.json()
    assert submit_res["score"] == 10.0
    assert submit_res["passed"] is True
    assert submit_res["task_points_awarded"] == 50

    # 8. Check student points summary endpoint
    resp = await client.get("/student/points", headers={"Authorization": "Bearer dev-token-student-u_student1"})
    assert resp.status_code == 200
    pts_res = resp.json()
    assert pts_res["total_points"] == 50
    assert pts_res["tasks_completed"] == 1
    delete_resp = await client.delete(
        f"/exams/{exam_id}",
        headers={"Authorization": teacher_auth},
    )
    assert delete_resp.status_code == 409


@pytest.mark.asyncio
async def test_create_exam_with_questions_and_publish_in_one_request(
    client: AsyncClient,
    db_session: AsyncSession,
):
    now = datetime.now(timezone.utc)
    course = Course(
        code="CS-BATCH",
        title="Batch Exam Course",
        teacher_id=db_session.test_teacher.id,
        is_published=True,
    )
    db_session.add(course)
    await db_session.commit()

    response = await client.post(
        "/exams",
        json={
            "course_id": str(course.id),
            "title": "One-request exam",
            "duration_minutes": 30,
            "pass_marks": 5,
            "start_at": (now - timedelta(minutes=1)).isoformat(),
            "end_at": (now + timedelta(hours=1)).isoformat(),
            "questions": [
                {
                    "text": "Which answer is correct?",
                    "marks": 10,
                    "position": 1,
                    "options": [
                        {"text": "Correct", "is_correct": True, "position": 1},
                        {"text": "Incorrect", "is_correct": False, "position": 2},
                    ],
                },
            ],
            "publish_immediately": True,
            "task_points": 25,
        },
        headers={"Authorization": "Bearer dev-token-teacher-u_teacher"},
    )

    assert response.status_code == 200
    exam = response.json()
    assert exam["status"] == "published"
    assert exam["total_marks"] == 10
    assert exam["pass_marks"] == 5

    detail = await client.get(
        f"/exams/{exam['id']}",
        headers={"Authorization": response.request.headers["Authorization"]},
    )
    assert detail.status_code == 200
    assert len(detail.json()["questions"]) == 1

    update_response = await client.patch(
        f"/exams/{exam['id']}",
        json={
            "title": "Updated one-request exam",
            "pass_marks": 4,
            "negative_marking": 1,
            "max_attempts": 2,
            "shuffle_questions": False,
            "show_review": False,
            "task_points": 30,
            "questions": [
                {
                    "text": "Updated question text",
                    "marks": 8,
                    "position": 1,
                    "options": [
                        {"text": "New correct", "is_correct": True, "position": 1},
                        {"text": "New incorrect", "is_correct": False, "position": 2},
                    ],
                },
            ],
        },
        headers={"Authorization": response.request.headers["Authorization"]},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated one-request exam"
    assert update_response.json()["total_marks"] == 8
    updated_detail = await client.get(
        f"/exams/{exam['id']}",
        headers={"Authorization": response.request.headers["Authorization"]},
    )
    assert updated_detail.json()["questions"][0]["text"] == "Updated question text"

    task_result = await db_session.execute(
        select(Task).where(Task.exam_id == uuid.UUID(exam["id"]))
    )
    assert task_result.scalar_one().points == 30

    delete_response = await client.delete(
        f"/exams/{exam['id']}",
        headers={"Authorization": response.request.headers["Authorization"]},
    )
    assert delete_response.status_code == 204
    task_result = await db_session.execute(
        select(Task).where(Task.exam_id == uuid.UUID(exam["id"]))
    )
    assert task_result.scalar_one_or_none() is None

    missing_exam = await client.get(
        f"/exams/{exam['id']}",
        headers={"Authorization": response.request.headers["Authorization"]},
    )
    assert missing_exam.status_code == 404
