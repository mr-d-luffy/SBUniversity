import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.deps import get_current_user
from app.db.models.course import Course, CourseTeacher
from app.db.models.exam import AttemptAnswer, Exam, Question, QuestionOption
from app.db.models.result import Result
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.repositories.course_repository import CourseRepository
from app.repositories.result_repository import ResultRepository
from app.schemas.result import PerQuestionReview, ResultDetailResponse, ResultResponse
from app.services.exam_service import ExamService

router = APIRouter(prefix="/results", tags=["Results"])


@router.get("", response_model=List[ResultResponse])
async def list_results(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ResultRepository(db)
    if current_user.role == UserRole.STUDENT:
        results, _ = await repo.list_results(student_id=current_user.id)
    elif current_user.role == UserRole.TEACHER:
        courses_stmt = select(Course.id).where(
            or_(
                Course.teacher_id == current_user.id,
                Course.teacher_assignments.any(
                    CourseTeacher.teacher_id == current_user.id
                ),
            )
        )
        course_ids = list((await db.scalars(courses_stmt)).all())
        results, _ = await repo.list_results(course_ids=course_ids)
    else:
        results, _ = await repo.list_results()
    return results


@router.get("/{result_id}", response_model=ResultDetailResponse)
async def get_result_detail(
    result_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ResultRepository(db)
    result = await repo.get_by_id(result_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    # Ownership check
    if current_user.role == UserRole.STUDENT and result.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if current_user.role == UserRole.TEACHER and not await CourseRepository(
        db
    ).is_teacher_assigned(result.exam.course_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Result not found"
        )

    reviews = []
    if result.exam.show_review:
        # Load questions & options and student answers
        stmt_q = select(Question).options(selectinload(Question.options)).where(Question.exam_id == result.exam_id).order_by(Question.position)
        questions = (await db.execute(stmt_q)).scalars().all()

        stmt_ans = select(AttemptAnswer).where(AttemptAnswer.attempt_id == result.attempt_id)
        answers = (await db.execute(stmt_ans)).scalars().all()
        answers_map = {a.question_id: a.selected_option_id for a in answers}

        for q in questions:
            selected_opt_id = answers_map.get(q.id)
            correct_opt = next((o for o in q.options if o.is_correct), None)
            correct_opt_id = correct_opt.id if correct_opt else None
            is_correct = (selected_opt_id == correct_opt_id) if selected_opt_id else False

            reviews.append(
                PerQuestionReview(
                    question_id=q.id,
                    question_text=q.text,
                    marks=float(q.marks),
                    explanation=q.explanation,
                    selected_option_id=selected_opt_id,
                    correct_option_id=correct_opt_id,
                    is_correct=is_correct,
                    options=[{"id": str(o.id), "text": o.text, "is_correct": o.is_correct} for o in q.options],
                )
            )

    return ResultDetailResponse(
        id=result.id,
        attempt_id=result.attempt_id,
        exam_id=result.exam_id,
        student_id=result.student_id,
        score=float(result.score),
        total_marks=float(result.total_marks),
        percentage=float(result.percentage),
        grade=result.grade,
        passed=result.passed,
        time_taken_sec=result.time_taken_sec,
        rank_in_exam=result.rank_in_exam,
        pdf_path=result.pdf_path,
        created_at=result.created_at,
        exam_title=result.exam.title,
        course_title=result.exam.course.title if result.exam.course else "Course",
        student_name=result.student.full_name if result.student else "Student",
        reviews=reviews,
    )


@router.get("/{result_id}/pdf")
async def download_result_pdf(
    result_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExamService(db)
    pdf_bytes = await service.get_or_generate_result_pdf(result_id, current_user)

    filename = f"result-{result_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
