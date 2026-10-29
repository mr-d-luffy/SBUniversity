import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.deps import get_current_user, require_role
from app.db.models.certificate import Certificate
from app.db.models.course import Course, Enrollment, EnrollmentStatus
from app.db.models.exam import Exam, ExamStatus
from app.db.models.notice import Notice, NoticeAudience, NoticeStatus
from app.db.models.result import Result
from app.db.models.task import (
    CompletionStatus,
    Task,
    TaskAssignmentScope,
    TaskCompletion,
    TaskRecipient,
    TaskStatus,
)
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.repositories.course_repository import CourseRepository
from app.schemas.course import EnrollmentResponse
from app.schemas.task import StudentPointsResponse
from app.schemas.user import VirtualIDCardResponse
from app.services.ranking_service import RankingService
from app.services.task_service import TaskService
from app.services.user_service import UserService

router = APIRouter(prefix="/student", tags=["Student"], dependencies=[Depends(require_role(UserRole.STUDENT))])


@router.get("/dashboard")
async def get_student_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    # 1. Enrolled courses + progress
    enrollments_stmt = (
        select(Enrollment)
        .options(selectinload(Enrollment.course))
        .where(Enrollment.student_id == current_user.id, Enrollment.status == EnrollmentStatus.ACTIVE)
    )
    enrollments_res = await db.execute(enrollments_stmt)
    enrollments = list(enrollments_res.scalars().all())
    enrolled_course_ids = [e.course_id for e in enrollments]

    # 2. Upcoming exams
    upcoming_exams = []
    if enrolled_course_ids:
        exams_stmt = (
            select(Exam)
            .options(selectinload(Exam.course))
            .where(
                Exam.course_id.in_(enrolled_course_ids),
                Exam.status == ExamStatus.PUBLISHED,
                Exam.end_at > func.now(),
            )
            .order_by(Exam.start_at.asc())
            .limit(5)
        )
        exams_res = await db.execute(exams_stmt)
        upcoming_exams = [
            {
                "id": str(e.id),
                "title": e.title,
                "course_title": e.course.title if e.course else "Course",
                "duration_minutes": e.duration_minutes,
                "start_at": e.start_at.isoformat(),
                "end_at": e.end_at.isoformat(),
                "total_marks": float(e.total_marks),
            }
            for e in exams_res.scalars().all()
        ]

    # 3. Recent results
    results_stmt = (
        select(Result)
        .options(selectinload(Result.exam).selectinload(Exam.course))
        .where(Result.student_id == current_user.id)
        .order_by(Result.created_at.desc())
        .limit(5)
    )
    results_res = await db.execute(results_stmt)
    recent_results = [
        {
            "id": str(r.id),
            "exam_title": r.exam.title if r.exam else "Exam",
            "course_title": r.exam.course.title if r.exam and r.exam.course else "Course",
            "score": float(r.score),
            "total_marks": float(r.total_marks),
            "percentage": float(r.percentage),
            "passed": r.passed,
            "grade": r.grade,
            "created_at": r.created_at.isoformat(),
        }
        for r in results_res.scalars().all()
    ]

    # 4. Open tasks
    open_tasks = []
    tasks_stmt = (
        select(Task)
        .options(selectinload(Task.course))
        .where(
            Task.status == TaskStatus.ACTIVE,
            or_(
                and_(
                    Task.assignment_scope == TaskAssignmentScope.ALL_STUDENTS,
                    Task.course_id.in_(enrolled_course_ids),
                ),
                and_(
                    Task.assignment_scope == TaskAssignmentScope.SELECTED_STUDENTS,
                    Task.id.in_(
                        select(TaskRecipient.task_id).where(
                            TaskRecipient.student_id == current_user.id
                        )
                    ),
                ),
            ),
        )
        .order_by(Task.created_at.desc())
        .limit(6)
    )
    tasks_res = await db.execute(tasks_stmt)
    tasks = list(tasks_res.scalars().all())
    completions_by_task_id = {}
    if tasks:
        completions_stmt = select(TaskCompletion).where(
            TaskCompletion.task_id.in_([task.id for task in tasks]),
            TaskCompletion.student_id == current_user.id,
        )
        completions_res = await db.execute(completions_stmt)
        completions_by_task_id = {
            completion.task_id: completion for completion in completions_res.scalars().all()
        }

    for t in tasks:
        comp = completions_by_task_id.get(t.id)
        my_status = comp.status.value if comp else "open"
        open_tasks.append({
            "id": str(t.id),
            "title": t.title,
            "course": t.course.title if t.course else "Course",
            "points": t.points,
            "type": t.type.value,
            "due": t.due_at.strftime("%b %d") if t.due_at else None,
            "status": my_status,
        })

    # 5. Points & Ranking
    task_service = TaskService(db)
    points_summary = await task_service.get_student_points(current_user.id)

    # 6. Certificates count
    certs_cnt_res = await db.execute(select(func.count(Certificate.id)).where(Certificate.student_id == current_user.id, Certificate.revoked_at.is_(None)))
    certs_count = certs_cnt_res.scalar() or 0

    return {
        "enrolled_courses": [
            {
                "id": str(e.course.id),
                "code": e.course.code,
                "title": e.course.title,
                "progress_percent": float(e.progress_percent),
            }
            for e in enrollments if e.course
        ],
        "upcoming_exams": upcoming_exams,
        "recent_results": recent_results,
        "open_tasks": open_tasks,
        "total_task_points": points_summary.total_points,
        "tasks_completed": points_summary.tasks_completed,
        "rank": points_summary.rank,
        "certificates_earned": certs_count,
    }


@router.get("/id-card", response_model=VirtualIDCardResponse)
async def get_student_id_card(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    return await service.get_virtual_id_card(current_user)


@router.get("/courses", response_model=List[EnrollmentResponse])
async def get_student_courses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    course_repo = CourseRepository(db)
    return await course_repo.list_student_enrollments(current_user.id)


@router.get("/course-catalog")
async def list_course_catalog(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    enrolled = select(Enrollment.course_id).where(Enrollment.student_id == current_user.id, Enrollment.status == EnrollmentStatus.ACTIVE)
    rows = (await db.execute(select(Course).where(Course.is_published.is_(True)).order_by(Course.title))).scalars().all()
    return [{"id": str(course.id), "code": course.code, "title": course.title, "description": course.description, "enrolled": course.id in set((await db.execute(enrolled)).scalars().all())} for course in rows]


@router.post("/courses/{course_id}/enroll", status_code=status.HTTP_201_CREATED)
async def enroll_in_course(course_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    course = await db.get(Course, course_id)
    if not course or not course.is_published:
        raise HTTPException(status_code=404, detail="Published course not found")
    enrollment = await db.scalar(select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.student_id == current_user.id))
    if enrollment:
        if enrollment.status == EnrollmentStatus.DROPPED:
            enrollment.status = EnrollmentStatus.ACTIVE
            await db.commit()
        return {"message": "You are enrolled in this course"}
    db.add(Enrollment(course_id=course_id, student_id=current_user.id, status=EnrollmentStatus.ACTIVE))
    await db.commit()
    return {"message": "You are enrolled in this course"}


@router.get("/points", response_model=StudentPointsResponse)
async def get_student_points(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    return await service.get_student_points(current_user.id)
