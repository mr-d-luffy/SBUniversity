from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Course,
    Enrollment,
    EnrollmentStatus,
    Exam,
    ExamAttempt,
    ExamStatus,
    Question,
    QuestionOption,
    Result,
    User,
    UserRole,
    UserStatus,
)


async def create_exam_result(
    db_session: AsyncSession,
    course: Course,
    student: User,
    title: str,
) -> tuple[Exam, Result]:
    now = datetime.now(UTC)
    exam = Exam(
        course_id=course.id,
        created_by=course.teacher_id,
        title=title,
        duration_minutes=30,
        total_marks=1,
        pass_marks=1,
        max_attempts=1,
        start_at=now - timedelta(hours=1),
        end_at=now + timedelta(hours=1),
        status=ExamStatus.PUBLISHED,
    )
    db_session.add(exam)
    await db_session.flush()
    question = Question(
        exam_id=exam.id,
        text=f"Question for {title}",
        marks=1,
        position=1,
        explanation="Answer explanation",
    )
    db_session.add(question)
    await db_session.flush()
    db_session.add_all(
        [
            QuestionOption(
                question_id=question.id,
                text="Correct answer",
                is_correct=True,
                position=1,
            ),
            QuestionOption(
                question_id=question.id,
                text="Incorrect answer",
                is_correct=False,
                position=2,
            ),
        ]
    )
    attempt = ExamAttempt(
        exam_id=exam.id,
        student_id=student.id,
        attempt_no=1,
        expires_at=now + timedelta(hours=1),
    )
    db_session.add(attempt)
    await db_session.flush()
    result = Result(
        attempt_id=attempt.id,
        exam_id=exam.id,
        student_id=student.id,
        score=1,
        total_marks=1,
        percentage=100,
        grade="A",
        passed=True,
        time_taken_sec=30,
    )
    db_session.add(result)
    await db_session.flush()
    return exam, result


@pytest.mark.asyncio
async def test_teacher_results_and_exam_details_are_limited_to_assigned_courses(
    client: AsyncClient,
    db_session: AsyncSession,
):
    teacher = db_session.test_teacher
    student = db_session.test_student1
    assigned_course = Course(
        code="ACCESS-101",
        title="Assigned Course",
        teacher_id=teacher.id,
        is_published=True,
    )
    other_teacher = User(
        clerk_user_id="u_unassigned_teacher",
        email="unassigned.teacher@sbuniversity.edu",
        full_name="Unassigned Teacher",
        role=UserRole.TEACHER,
        status=UserStatus.ACTIVE,
    )
    db_session.add_all([assigned_course, other_teacher])
    await db_session.flush()
    other_course = Course(
        code="ACCESS-102",
        title="Other Course",
        teacher_id=other_teacher.id,
        is_published=True,
    )
    db_session.add_all(
        [
            other_course,
            Enrollment(
                student_id=student.id,
                course_id=assigned_course.id,
                status=EnrollmentStatus.ACTIVE,
            ),
        ]
    )
    await db_session.flush()
    assigned_exam, assigned_result = await create_exam_result(
        db_session, assigned_course, student, "Assigned Exam"
    )
    other_exam, other_result = await create_exam_result(
        db_session, other_course, student, "Other Exam"
    )
    await db_session.commit()

    teacher_headers = {"Authorization": "Bearer dev-token-teacher-u_teacher"}
    listed_results = await client.get("/results", headers=teacher_headers)
    assert listed_results.status_code == 200
    assert {result["id"] for result in listed_results.json()} == {
        str(assigned_result.id)
    }

    assigned_detail = await client.get(
        f"/exams/{assigned_exam.id}", headers=teacher_headers
    )
    assert assigned_detail.status_code == 200
    assert assigned_detail.json()["questions"][0]["options"][0]["is_correct"] is True

    student_detail = await client.get(
        f"/exams/{assigned_exam.id}",
        headers={"Authorization": "Bearer dev-token-student-u_student1"},
    )
    assert student_detail.status_code == 200
    assert all(
        option["is_correct"] is None
        for option in student_detail.json()["questions"][0]["options"]
    )

    other_result_detail = await client.get(
        f"/results/{other_result.id}", headers=teacher_headers
    )
    assert other_result_detail.status_code == 404
    other_result_pdf = await client.get(
        f"/results/{other_result.id}/pdf", headers=teacher_headers
    )
    assert other_result_pdf.status_code == 403
    other_exam_detail = await client.get(
        f"/exams/{other_exam.id}", headers=teacher_headers
    )
    assert other_exam_detail.status_code == 404


@pytest.mark.asyncio
async def test_student_cannot_read_exam_details_without_active_enrollment(
    client: AsyncClient,
    db_session: AsyncSession,
):
    course = Course(
        code="ACCESS-201",
        title="Unenrolled Course",
        teacher_id=db_session.test_teacher.id,
        is_published=True,
    )
    db_session.add(course)
    await db_session.flush()
    exam, _ = await create_exam_result(
        db_session, course, db_session.test_student1, "Unenrolled Exam"
    )
    await db_session.commit()

    response = await client.get(
        f"/exams/{exam.id}",
        headers={"Authorization": "Bearer dev-token-student-u_student2"},
    )

    assert response.status_code == 404
