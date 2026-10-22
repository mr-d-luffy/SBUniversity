import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.deps import get_current_user, require_role
from app.db.models.course import Course, CourseTeacher, Enrollment, EnrollmentStatus
from app.db.models.exam import AttemptAnswer, AttemptStatus, Exam, ExamAttempt, ExamStatus, Question, QuestionOption
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.schemas.exam import (
    AutosaveAnswerRequest,
    AutosaveAnswerResponse,
    ExamCreate,
    ExamDetailResponse,
    ExamPublishRequest,
    ExamResponse,
    ExamUpdate,
    QuestionCreate,
    QuestionOptionResponse,
    QuestionResponse,
    StartAttemptResponse,
    SubmitAttemptResponse,
)
from app.services.exam_service import ExamService

router = APIRouter(prefix="", tags=["Exams"])


@router.get("/exams", response_model=List[ExamResponse])
async def list_exams(
    course_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Exam).options(
        selectinload(Exam.course),
        selectinload(Exam.questions),
        selectinload(Exam.task),
    )

    if current_user.role == UserRole.STUDENT:
        # Enrolled published courses only
        enrolled_stmt = select(Enrollment.course_id).where(
            Enrollment.student_id == current_user.id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
        enrolled_ids = (await db.execute(enrolled_stmt)).scalars().all()
        stmt = stmt.where(Exam.course_id.in_(enrolled_ids), Exam.status == ExamStatus.PUBLISHED)
    elif current_user.role == UserRole.TEACHER:
        # Teacher's own courses
        courses_stmt = select(Course.id).where(
            or_(
                Course.teacher_id == current_user.id,
                Course.teacher_assignments.any(
                    CourseTeacher.teacher_id == current_user.id
                ),
            )
        )
        teacher_course_ids = (await db.execute(courses_stmt)).scalars().all()
        stmt = stmt.where(Exam.course_id.in_(teacher_course_ids))

    if course_id:
        stmt = stmt.where(Exam.course_id == course_id)

    stmt = stmt.order_by(Exam.start_at.desc())
    res = await db.execute(stmt)
    exams = list(res.scalars().all())

    # Map task points
    result = []
    for ex in exams:
        ex_dict = ExamResponse.model_validate(ex)
        ex_dict.task_points = ex.task.points if ex.task else 0
        ex_dict.course_title = ex.course.title if ex.course else None
        ex_dict.questions_count = len(ex.questions)
        result.append(ex_dict)
    return result


@router.get("/exams/{exam_id}", response_model=ExamDetailResponse)
async def get_exam_detail(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Exam)
        .options(
            selectinload(Exam.questions).selectinload(Question.options),
            selectinload(Exam.task),
        )
        .where(Exam.id == exam_id)
    )
    res = await db.execute(stmt)
    exam = res.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    # If student, do not show correct answers
    is_privileged = current_user.role in (UserRole.TEACHER, UserRole.ADMIN)

    questions_res = []
    for q in exam.questions:
        options_res = [
            QuestionOptionResponse(
                id=o.id,
                text=o.text,
                position=o.position,
                is_correct=o.is_correct if is_privileged else None,
            )
            for o in q.options
        ]
        questions_res.append(
            QuestionResponse(
                id=q.id,
                text=q.text,
                marks=float(q.marks),
                position=q.position,
                explanation=q.explanation if is_privileged else None,
                options=options_res,
            )
        )

    resp = ExamDetailResponse.model_validate(exam)
    resp.questions = questions_res
    resp.task_points = exam.task.points if exam.task else 0
    return resp


@router.post("/exams", response_model=ExamResponse)
async def create_exam(
    data: ExamCreate,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    service = ExamService(db)
    exam = await service.create_exam(data, current_user)
    return exam


@router.patch("/exams/{exam_id}", response_model=ExamResponse)
async def update_exam(
    exam_id: uuid.UUID,
    data: ExamUpdate,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    service = ExamService(db)
    return await service.update_exam(exam_id, data, current_user)


@router.post("/exams/{exam_id}/publish", response_model=ExamResponse)
async def publish_exam(
    exam_id: uuid.UUID,
    data: ExamPublishRequest,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    service = ExamService(db)
    return await service.publish_exam(exam_id, data, current_user)


@router.post("/exams/{exam_id}/close", response_model=ExamResponse)
async def close_exam(
    exam_id: uuid.UUID,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    service = ExamService(db)
    return await service.close_exam(exam_id, current_user)

@router.delete("/exams/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exam(
    exam_id: uuid.UUID,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    service = ExamService(db)
    await service.delete_exam(exam_id, current_user)


@router.post("/exams/{exam_id}/questions", response_model=QuestionResponse)
async def add_exam_question(
    exam_id: uuid.UUID,
    data: QuestionCreate,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    service = ExamService(db)
    q = await service.add_question(exam_id, data, current_user)
    opts = [QuestionOptionResponse.model_validate(o) for o in q.options]
    return QuestionResponse(
        id=q.id,
        text=q.text,
        marks=float(q.marks),
        position=q.position,
        explanation=q.explanation,
        options=opts,
    )


@router.post("/exams/{exam_id}/attempts", response_model=StartAttemptResponse)
async def start_exam_attempt(
    exam_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db),
):
    service = ExamService(db)
    return await service.start_attempt(exam_id, current_user)


@router.get("/attempts/{attempt_id}")
async def get_attempt(
    attempt_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ExamAttempt)
        .options(
            selectinload(ExamAttempt.exam).selectinload(Exam.questions).selectinload(Question.options),
            selectinload(ExamAttempt.answers),
        )
        .where(ExamAttempt.id == attempt_id)
    )
    res = await db.execute(stmt)
    attempt = res.scalar_one_or_none()
    if not attempt or (current_user.role == UserRole.STUDENT and attempt.student_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    answers_map = {str(a.question_id): str(a.selected_option_id) if a.selected_option_id else None for a in attempt.answers}

    # Hide answers
    safe_questions = []
    for q in attempt.exam.questions:
        safe_questions.append({
            "id": str(q.id),
            "text": q.text,
            "marks": float(q.marks),
            "position": q.position,
            "options": [{"id": str(o.id), "text": o.text, "position": o.position} for o in q.options],
            "saved_option_id": answers_map.get(str(q.id)),
        })

    return {
        "attempt_id": str(attempt.id),
        "exam_id": str(attempt.exam_id),
        "exam_title": attempt.exam.title,
        "status": attempt.status.value,
        "started_at": attempt.started_at.isoformat(),
        "expires_at": attempt.expires_at.isoformat(),
        "duration_minutes": attempt.exam.duration_minutes,
        "questions": safe_questions,
    }


@router.put("/attempts/{attempt_id}/answers/{question_id}", response_model=AutosaveAnswerResponse)
async def autosave_answer(
    attempt_id: uuid.UUID,
    question_id: uuid.UUID,
    body: AutosaveAnswerRequest,
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db),
):
    service = ExamService(db)
    res = await service.autosave_answer(attempt_id, question_id, body.selected_option_id, current_user.id)
    return res


@router.post("/attempts/{attempt_id}/submit", response_model=SubmitAttemptResponse)
async def submit_exam_attempt(
    attempt_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db),
):
    service = ExamService(db)
    return await service.submit_attempt(attempt_id, current_user.id)
