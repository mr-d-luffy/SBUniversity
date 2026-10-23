import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.deps import get_current_user, require_role
from app.db.models.course import Course, CourseTeacher, Enrollment, EnrollmentStatus
from app.db.models.exam import Exam, ExamStatus
from app.db.models.notice import Notice, NoticeStatus
from app.db.models.result import Result
from app.db.models.task import CompletionStatus, Task, TaskCompletion
from app.db.models.user import User, UserRole, UserStatus
from app.db.session import get_db
from app.repositories.course_repository import CourseRepository
from app.schemas.result import ResultResponse
from app.schemas.task import TeacherTaskCourseOption, TeacherTaskStudentOption

router = APIRouter(prefix="/teacher", tags=["Teacher"], dependencies=[Depends(require_role([UserRole.TEACHER, UserRole.ADMIN]))])


@router.get("/dashboard")
async def get_teacher_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    # Courses taught by this teacher
    courses_stmt = select(Course).where(
        or_(
            Course.teacher_id == current_user.id,
            Course.teacher_assignments.any(
                CourseTeacher.teacher_id == current_user.id
            ),
        )
    )
    courses_res = await db.execute(courses_stmt)
    courses = list(courses_res.scalars().all())
    course_ids = [c.id for c in courses]

    exams_count = 0
    submissions_count = 0
    avg_score = 0.0
    pass_rate = 0.0
    pending_approvals = 0

    if course_ids:
        # Exams count
        ex_res = await db.execute(select(func.count(Exam.id)).where(Exam.course_id.in_(course_ids)))
        exams_count = ex_res.scalar() or 0

        # Submissions
        sub_stmt = (
            select(
                func.count(Result.id),
                func.avg(Result.percentage),
                func.count(Result.id).filter(Result.passed == True),
            )
            .join(Exam, Exam.id == Result.exam_id)
            .where(Exam.course_id.in_(course_ids))
        )
        sub_res = (await db.execute(sub_stmt)).one()
        submissions_count = sub_res[0] or 0
        avg_score = round(float(sub_res[1] or 0.0), 2)
        passed_cnt = sub_res[2] or 0
        pass_rate = round((passed_cnt / submissions_count * 100.0) if submissions_count > 0 else 0.0, 2)

        # Pending task approvals count
        task_stmt = (
            select(func.count(TaskCompletion.id))
            .join(Task, Task.id == TaskCompletion.task_id)
            .where(
                Task.course_id.in_(course_ids),
                TaskCompletion.status == CompletionStatus.PENDING_REVIEW,
            )
        )
        task_res = await db.execute(task_stmt)
        pending_approvals = task_res.scalar() or 0

    # Recent notices posted by this teacher
    notices_stmt = select(Notice).where(Notice.author_id == current_user.id).order_by(Notice.created_at.desc()).limit(5)
    notices_res = await db.execute(notices_stmt)
    recent_notices = [
        {
            "id": str(n.id),
            "title": n.title,
            "audience": n.audience.value,
            "priority": n.priority.value,
            "created_at": n.created_at.isoformat(),
        }
        for n in notices_res.scalars().all()
    ]

    return {
        "my_courses": [{"id": str(c.id), "code": c.code, "title": c.title, "is_published": c.is_published} for c in courses],
        "total_exams": exams_count,
        "total_submissions": submissions_count,
        "average_score": avg_score,
        "pass_rate": pass_rate,
        "pending_task_approvals": pending_approvals,
        "recent_notices": recent_notices,
    }


@router.get(
    "/task-courses",
    response_model=List[TeacherTaskCourseOption],
)
async def list_courses_for_task_creation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Course.id, Course.code, Course.title)
    if current_user.role == UserRole.TEACHER:
        stmt = stmt.where(or_(
            Course.teacher_id == current_user.id,
            Course.teacher_assignments.any(CourseTeacher.teacher_id == current_user.id),
        ))
    stmt = stmt.order_by(Course.title)
    rows = (await db.execute(stmt)).all()
    return [
        TeacherTaskCourseOption(id=row.id, title=row.title, code=row.code)
        for row in rows
    ]


@router.get(
    "/task-students",
    response_model=List[TeacherTaskStudentOption],
)
async def list_students_for_task_creation(
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(User.id, User.full_name, User.email)
        .where(User.role == UserRole.STUDENT, User.status == UserStatus.ACTIVE)
        .order_by(User.full_name)
    )
    rows = (await db.execute(stmt)).all()
    return [
        TeacherTaskStudentOption(id=row.id, full_name=row.full_name, email=row.email)
        for row in rows
    ]


@router.get(
    "/courses/{course_id}/students",
    response_model=List[TeacherTaskStudentOption],
)
async def list_course_students_for_task(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    stmt = (
        select(User.id, User.full_name, User.email)
        .join(Enrollment, Enrollment.student_id == User.id)
        .where(
            Enrollment.course_id == course_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
            User.role == UserRole.STUDENT,
            User.status == UserStatus.ACTIVE,
        )
        .order_by(User.full_name)
    )
    rows = (await db.execute(stmt)).all()
    return [
        TeacherTaskStudentOption(id=row.id, full_name=row.full_name, email=row.email)
        for row in rows
    ]


@router.get("/courses/{course_id}/results", response_model=List[ResultResponse])
async def get_course_results(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    course_stmt = select(Course).where(Course.id == course_id)
    course = (await db.execute(course_stmt)).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if current_user.role == UserRole.TEACHER and not await CourseRepository(db).is_teacher_assigned(
        course.id, current_user.id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    results_stmt = (
        select(Result)
        .join(Exam, Exam.id == Result.exam_id)
        .where(Exam.course_id == course_id)
        .order_by(Result.created_at.desc())
    )
    res = await db.execute(results_stmt)
    return list(res.scalars().all())
