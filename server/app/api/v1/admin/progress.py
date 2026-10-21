import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.deps import get_current_user, require_role
from app.db.models.course import Course, Enrollment
from app.db.models.exam import Exam
from app.db.models.task import (
    CompletionStatus,
    Task,
    TaskAssignmentScope,
    TaskCompletion,
    TaskRecipient,
    TaskStatus,
)
from app.db.models.user import StudentProfile, User, UserRole
from app.db.session import get_db
from app.schemas.certificate import CertificateResponse, RevokeCertificateRequest
from app.services.certificate_service import CertificateService
from app.services.task_service import TaskService

router = APIRouter(prefix="/progress", tags=["Admin Progress"], dependencies=[Depends(require_role(UserRole.ADMIN))])


@router.get("/students")
async def get_students_progress(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(User)
        .options(
            selectinload(User.student_profile),
            selectinload(User.enrollments).selectinload(Enrollment.course),
        )
        .where(User.role == UserRole.STUDENT)
    )
    if search:
        term = f"%{search.lower()}%"
        stmt = stmt.where(func.lower(User.full_name).like(term) | func.lower(User.email).like(term))

    count_stmt = select(func.count(User.id)).where(User.role == UserRole.STUDENT)
    if search:
        count_stmt = count_stmt.where(func.lower(User.full_name).like(term) | func.lower(User.email).like(term))

    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    res = await db.execute(stmt)
    students = list(res.scalars().all())

    student_ids = [student.id for student in students]
    task_progress: dict[tuple[uuid.UUID, uuid.UUID], tuple[int, int]] = {}
    if student_ids:
        progress_stmt = (
            select(
                Enrollment.student_id,
                Enrollment.course_id,
                func.count(Task.id),
                func.coalesce(
                    func.sum(
                        case(
                            (TaskCompletion.status == CompletionStatus.COMPLETED, 1),
                            else_=0,
                        )
                    ),
                    0,
                ),
            )
            .join(
                Task,
                and_(
                    Task.course_id == Enrollment.course_id,
                    Task.status == TaskStatus.ACTIVE,
                ),
            )
            .outerjoin(
                TaskRecipient,
                and_(
                    TaskRecipient.task_id == Task.id,
                    TaskRecipient.student_id == Enrollment.student_id,
                ),
            )
            .outerjoin(
                TaskCompletion,
                and_(
                    TaskCompletion.task_id == Task.id,
                    TaskCompletion.student_id == Enrollment.student_id,
                ),
            )
            .where(
                Enrollment.student_id.in_(student_ids),
                or_(
                    Task.assignment_scope == TaskAssignmentScope.ALL_STUDENTS,
                    TaskRecipient.student_id == Enrollment.student_id,
                ),
            )
            .group_by(Enrollment.student_id, Enrollment.course_id)
        )
        progress_rows = (await db.execute(progress_stmt)).all()
        task_progress = {
            (student_id, course_id): (int(completed_count), int(total_count))
            for student_id, course_id, total_count, completed_count in progress_rows
        }

    items = []
    task_service = TaskService(db)
    for s in students:
        pts = await task_service.get_student_points(s.id)
        courses_data = []
        for enrollment in s.enrollments:
            completed_count, total_count = task_progress.get(
                (s.id, enrollment.course_id), (0, 0)
            )
            progress_percent = (
                round((completed_count / total_count) * 100, 2)
                if total_count
                else 0.0
            )
            courses_data.append(
                {
                    "course_id": str(enrollment.course_id),
                    "course_title": enrollment.course.title if enrollment.course else "Course",
                    "progress_percent": progress_percent,
                    "completed_tasks": completed_count,
                    "total_tasks": total_count,
                    "status": enrollment.status.value,
                }
            )
        items.append({
            "student_id": str(s.id),
            "name": s.full_name,
            "email": s.email,
            "student_code": s.student_profile.student_code if s.student_profile else "SBU-0000",
            "total_points": pts.total_points,
            "tasks_completed": pts.tasks_completed,
            "rank": pts.rank,
            "courses": courses_data,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/tasks/completions/{completion_id}/revoke")
async def revoke_student_task_completion(
    completion_id: uuid.UUID,
    reason: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    comp = await service.revoke_completion(completion_id, current_user, reason)
    return {
        "completion_id": str(comp.id),
        "status": comp.status.value,
        "points_awarded": comp.points_awarded,
    }


@router.post("/certificates/{certificate_id}/revoke", response_model=CertificateResponse)
async def revoke_student_certificate(
    certificate_id: uuid.UUID,
    body: RevokeCertificateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CertificateService(db)
    cert = await service.revoke_certificate(certificate_id, current_user, body.reason)
    return cert
