import json
from typing import List

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.core.redis import get_redis_client
from app.db.models.course import Course, Enrollment
from app.db.models.exam import Exam
from app.db.models.result import Result
from app.db.models.task import CompletionStatus, Task, TaskCompletion
from app.db.models.user import (
    StudentProfile,
    TeacherProfile,
    User,
    UserRole,
    UserStatus,
)
from app.schemas.analytics import (
    OverviewAnalyticsResponse,
    PublicStatsResponse,
    StudentAnalyticsItem,
    TeacherAnalyticsItem,
)


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_overview_analytics(self) -> OverviewAnalyticsResponse:
        redis = await get_redis_client()
        cached = await redis.get("cache:admin:analytics:overview")
        if cached:
            try:
                return OverviewAnalyticsResponse(**json.loads(cached))
            except (json.JSONDecodeError, TypeError, ValidationError) as exc:
                logger.warning("Ignoring malformed overview analytics cache entry: %s", exc)

        row = (
            await self.db.execute(
                select(
                    select(func.count(User.id))
                    .where(
                        User.role == UserRole.STUDENT,
                        User.status != UserStatus.DELETED,
                    )
                    .scalar_subquery()
                    .label("total_students"),
                    select(func.count(User.id))
                    .where(
                        User.role == UserRole.STUDENT,
                        User.status == UserStatus.ACTIVE,
                    )
                    .scalar_subquery()
                    .label("active_students"),
                    select(func.count(User.id))
                    .where(
                        User.role == UserRole.TEACHER,
                        User.status == UserStatus.ACTIVE,
                    )
                    .scalar_subquery()
                    .label("total_teachers"),
                    select(func.count(Course.id)).scalar_subquery().label("total_courses"),
                    select(func.count(Exam.id)).scalar_subquery().label("total_exams"),
                    select(func.count(Result.id))
                    .scalar_subquery()
                    .label("total_submissions"),
                    select(func.avg(Result.percentage))
                    .scalar_subquery()
                    .label("average_score"),
                    select(func.count(Result.id))
                    .where(Result.passed.is_(True))
                    .scalar_subquery()
                    .label("passed_submissions"),
                    select(func.count(Task.id)).scalar_subquery().label("total_tasks"),
                    select(func.count(TaskCompletion.id))
                    .where(TaskCompletion.status == CompletionStatus.COMPLETED)
                    .scalar_subquery()
                    .label("completed_tasks"),
                    select(func.coalesce(func.sum(TaskCompletion.points_awarded), 0))
                    .where(TaskCompletion.status == CompletionStatus.COMPLETED)
                    .scalar_subquery()
                    .label("task_points"),
                )
            )
        ).one()
        total_submissions = row.total_submissions or 0
        pass_rate = round(
            (row.passed_submissions / total_submissions * 100.0)
            if total_submissions
            else 0.0,
            2,
        )

        response = OverviewAnalyticsResponse(
            total_students=row.total_students or 0,
            active_students_now=row.active_students or 0,
            total_teachers=row.total_teachers or 0,
            total_courses=row.total_courses or 0,
            total_exams=row.total_exams or 0,
            total_submissions=total_submissions,
            overall_average_score=round(float(row.average_score or 0.0), 2),
            overall_pass_rate=pass_rate,
            total_tasks=row.total_tasks or 0,
            total_task_completions=row.completed_tasks or 0,
            total_task_points_awarded=int(row.task_points or 0),
        )

        await redis.set(
            "cache:admin:analytics:overview",
            json.dumps(response.model_dump()),
            ex=45,
        )
        return response

    async def get_teacher_analytics(self) -> List[TeacherAnalyticsItem]:
        stmt = (
            select(User)
            .options(
                selectinload(User.teacher_profile).selectinload(TeacherProfile.department),
            )
            .where(User.role == UserRole.TEACHER, User.status == UserStatus.ACTIVE)
        )
        res = await self.db.execute(stmt)
        teachers = list(res.scalars().all())
        teacher_ids = [teacher.id for teacher in teachers]
        if not teacher_ids:
            return []

        course_counts = dict(
            (
                await self.db.execute(
                    select(Course.teacher_id, func.count(Course.id))
                    .where(Course.teacher_id.in_(teacher_ids))
                    .group_by(Course.teacher_id)
                )
            ).all()
        )
        exam_counts = dict(
            (
                await self.db.execute(
                    select(Course.teacher_id, func.count(Exam.id))
                    .join(Exam, Exam.course_id == Course.id)
                    .where(Course.teacher_id.in_(teacher_ids))
                    .group_by(Course.teacher_id)
                )
            ).all()
        )
        result_stats = {
            teacher_id: (count, average, passed)
            for teacher_id, count, average, passed in (
                await self.db.execute(
                    select(
                        Course.teacher_id,
                        func.count(Result.id),
                        func.avg(Result.percentage),
                        func.count(Result.id).filter(Result.passed.is_(True)),
                    )
                    .join(Exam, Exam.course_id == Course.id)
                    .join(Result, Result.exam_id == Exam.id)
                    .where(Course.teacher_id.in_(teacher_ids))
                    .group_by(Course.teacher_id)
                )
            ).all()
        }

        items: List[TeacherAnalyticsItem] = []
        for teacher in teachers:
            sub_count, average, passed_count = result_stats.get(
                teacher.id, (0, 0, 0)
            )
            sub_count = sub_count or 0
            dept_name = (
                teacher.teacher_profile.department.name
                if teacher.teacher_profile and teacher.teacher_profile.department
                else None
            )

            items.append(
                TeacherAnalyticsItem(
                    teacher_id=teacher.id,
                    teacher_name=teacher.full_name,
                    department_name=dept_name,
                    courses_count=course_counts.get(teacher.id, 0),
                    exams_created=exam_counts.get(teacher.id, 0),
                    total_submissions=sub_count,
                    average_score=round(float(average or 0.0), 2),
                    pass_rate=round(
                        (passed_count / sub_count * 100.0) if sub_count else 0.0,
                        2,
                    ),
                )
            )
        return items

    async def get_student_analytics(self, limit: int = 50) -> List[StudentAnalyticsItem]:
        stmt = (
            select(User)
            .options(
                selectinload(User.student_profile).selectinload(StudentProfile.department),
            )
            .where(User.role == UserRole.STUDENT, User.status == UserStatus.ACTIVE)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        students = list(res.scalars().all())
        student_ids = [student.id for student in students]
        if not student_ids:
            return []

        enrollment_counts = dict(
            (
                await self.db.execute(
                    select(Enrollment.student_id, func.count(Enrollment.id))
                    .where(Enrollment.student_id.in_(student_ids))
                    .group_by(Enrollment.student_id)
                )
            ).all()
        )
        result_stats = {
            student_id: (count, average)
            for student_id, count, average in (
                await self.db.execute(
                    select(
                        Result.student_id,
                        func.count(Result.id),
                        func.avg(Result.percentage),
                    )
                    .where(Result.student_id.in_(student_ids))
                    .group_by(Result.student_id)
                )
            ).all()
        }
        task_stats = {
            student_id: (count, points)
            for student_id, count, points in (
                await self.db.execute(
                    select(
                        TaskCompletion.student_id,
                        func.count(TaskCompletion.id),
                        func.sum(TaskCompletion.points_awarded),
                    )
                    .where(
                        TaskCompletion.student_id.in_(student_ids),
                        TaskCompletion.status == CompletionStatus.COMPLETED,
                    )
                    .group_by(TaskCompletion.student_id)
                )
            ).all()
        }

        items: List[StudentAnalyticsItem] = []
        for student in students:
            exams_taken, average = result_stats.get(student.id, (0, 0))
            tasks_completed, points = task_stats.get(student.id, (0, 0))
            profile = student.student_profile
            dept_name = (
                profile.department.name
                if profile and profile.department
                else None
            )
            student_code = profile.student_code if profile else "SBU-0000"
            items.append(
                StudentAnalyticsItem(
                    student_id=student.id,
                    student_name=student.full_name,
                    student_code=student_code,
                    department_name=dept_name,
                    courses_enrolled=enrollment_counts.get(student.id, 0),
                    exams_taken=exams_taken or 0,
                    average_score=round(float(average or 0.0), 2),
                    tasks_completed=tasks_completed or 0,
                    total_points=int(points or 0),
                )
            )
        return items

    async def get_public_stats(self) -> PublicStatsResponse:
        redis = await get_redis_client()
        cached = await redis.get("cache:public:stats")
        if cached:
            try:
                return PublicStatsResponse(**json.loads(cached))
            except (json.JSONDecodeError, TypeError, ValidationError) as exc:
                logger.warning("Ignoring malformed public stats cache entry: %s", exc)

        row = (
            await self.db.execute(
                select(
                    select(func.count(User.id))
                    .where(User.role == UserRole.STUDENT)
                    .scalar_subquery()
                    .label("students"),
                    select(func.count(Course.id))
                    .where(Course.is_published.is_(True))
                    .scalar_subquery()
                    .label("courses"),
                    select(func.count(Exam.id))
                    .where(Exam.status == "published")
                    .scalar_subquery()
                    .label("exams"),
                    select(func.count(Result.id))
                    .where(Result.passed.is_(True))
                    .scalar_subquery()
                    .label("certificates"),
                )
            )
        ).one()

        res = PublicStatsResponse(
            total_students=row.students,
            total_courses=row.courses,
            total_exams=row.exams,
            total_certificates_issued=row.certificates,
        )
        await redis.set("cache:public:stats", json.dumps(res.model_dump()), ex=300)
        return res
