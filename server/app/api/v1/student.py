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
from app.schemas.course import (
    CourseKeyActivationRequest,
    EnrollmentResponse,
    StudentCourseKeyRequestResponse,
)
from app.schemas.task import StudentPointsResponse
from app.schemas.user import VirtualIDCardResponse
from app.services.ranking_service import RankingService
from app.services.course_access_service import CourseAccessService, is_course_unlocked, unlocked_course_ids
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
    unlocked_ids = await unlocked_course_ids(db, current_user.id)
    enrollments = [enrollment for enrollment in enrollments if enrollment.course_id in unlocked_ids]
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
        .where(
            Result.student_id == current_user.id,
            Result.exam.has(Exam.course_id.in_(unlocked_ids)) if unlocked_ids else False,
        )
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
                    Task.course_id.in_(unlocked_ids) if unlocked_ids else False,
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
    certs_cnt_res = await db.execute(
        select(func.count(Certificate.id)).where(
            Certificate.student_id == current_user.id,
            Certificate.revoked_at.is_(None),
            Certificate.course_id.in_(unlocked_ids) if unlocked_ids else False,
        )
    )
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
    unlocked_ids = await unlocked_course_ids(db, current_user.id)
    return [
        enrollment
        for enrollment in await course_repo.list_student_enrollments(current_user.id)
        if enrollment.course_id in unlocked_ids
    ]


@router.get("/course-catalog")
async def list_course_catalog(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    enrolled = select(Enrollment.course_id).where(Enrollment.student_id == current_user.id, Enrollment.status == EnrollmentStatus.ACTIVE)
    rows = (await db.execute(select(Course).where(Course.is_published.is_(True)).order_by(Course.title))).scalars().all()
    enrolled_ids = set((await db.execute(enrolled)).scalars().all())
    unlocked_ids = await unlocked_course_ids(db, current_user.id)
    requests = await CourseAccessService(db).list_student_requests(current_user.id)
    latest_status = {}
    for request, _ in requests:
        latest_status.setdefault(request.course_id, request.status.value)
    return [
        {
            "id": str(course.id),
            "code": course.code,
            "title": course.title,
            "description": course.description,
            "price": course.price,
            "discount_percent": course.discount_percent,
            "enrolled": course.id in enrolled_ids,
            "unlocked": course.id in unlocked_ids,
            "key_request_status": latest_status.get(course.id),
        }
        for course in rows
    ]


@router.post("/courses/{course_id}/enroll", status_code=status.HTTP_201_CREATED)
async def enroll_in_course(course_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    course = await db.get(Course, course_id)
    if not course or not course.is_published:
        raise HTTPException(status_code=404, detail="Published course not found")
    if not await is_course_unlocked(db, current_user.id, course_id):
        raise HTTPException(status_code=403, detail="Unlock this course with an approved key first.")
    enrollment = await db.scalar(select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.student_id == current_user.id))
    if enrollment:
        if enrollment.status == EnrollmentStatus.DROPPED:
            enrollment.status = EnrollmentStatus.ACTIVE
            await db.commit()
        return {"message": "You are enrolled in this course"}
    db.add(Enrollment(course_id=course_id, student_id=current_user.id, status=EnrollmentStatus.ACTIVE))
    await db.commit()
    return {"message": "You are enrolled in this course"}


@router.get(
    "/course-key-requests",
    response_model=List[StudentCourseKeyRequestResponse],
)
async def list_my_course_key_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    requests = await CourseAccessService(db).list_student_requests(current_user.id)
    return [
        StudentCourseKeyRequestResponse(
            id=request.id,
            course_id=request.course_id,
            course_title=course.title,
            status=request.status.value,
            requested_at=request.requested_at,
            reviewed_at=request.reviewed_at,
            activated_at=request.activated_at,
        )
        for request, course in requests
    ]


@router.post(
    "/courses/{course_id}/key-requests",
    response_model=StudentCourseKeyRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_course_key(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    request = await CourseAccessService(db).request_key(course_id, current_user)
    course = await db.get(Course, course_id)
    return StudentCourseKeyRequestResponse(
        id=request.id,
        course_id=request.course_id,
        course_title=course.title,
        status=request.status.value,
        requested_at=request.requested_at,
    )


@router.post("/course-key-activations", status_code=status.HTTP_201_CREATED)
async def activate_course_key(
    data: CourseKeyActivationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    unlock = await CourseAccessService(db).activate_key(data.key, current_user)
    course = await db.get(Course, unlock.course_id)
    return {
        "course_id": str(unlock.course_id),
        "course_title": course.title if course else "Course",
        "unlocked_at": unlock.unlocked_at,
    }


@router.get("/points", response_model=StudentPointsResponse)
async def get_student_points(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    return await service.get_student_points(current_user.id)
