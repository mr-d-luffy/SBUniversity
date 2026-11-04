import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.task import (
    CompletionStatus,
    Task,
    TaskAssignmentScope,
    TaskCompletion,
    TaskRecipient,
    TaskStatus,
    TaskType,
    TaskVideoProgress,
)
from app.db.models.user import User


class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, task_id: uuid.UUID) -> Optional[Task]:
        stmt = select(Task).options(selectinload(Task.course), selectinload(Task.creator)).where(Task.id == task_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_exam_id(self, exam_id: uuid.UUID) -> Optional[Task]:
        stmt = select(Task).where(Task.exam_id == exam_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_tasks(
        self,
        course_id: Optional[uuid.UUID] = None,
        status: Optional[TaskStatus] = None,
        task_type: Optional[TaskType] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Task], int]:
        stmt = select(Task).options(selectinload(Task.course))
        count_stmt = select(func.count(Task.id))

        if course_id:
            stmt = stmt.where(Task.course_id == course_id)
            count_stmt = count_stmt.where(Task.course_id == course_id)
        if status:
            stmt = stmt.where(Task.status == status)
            count_stmt = count_stmt.where(Task.status == status)
        if task_type:
            stmt = stmt.where(Task.type == task_type)
            count_stmt = count_stmt.where(Task.type == task_type)

        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = stmt.order_by(Task.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        res = await self.db.execute(stmt)
        return list(res.scalars().all()), total

    async def list_student_tasks(
        self,
        student_id: uuid.UUID,
        course_ids: List[uuid.UUID],
        course_id: Optional[uuid.UUID] = None,
        completed_only: bool = False,
    ) -> List[Task]:
        completed_task_ids = select(TaskCompletion.task_id).where(
            TaskCompletion.student_id == student_id,
            TaskCompletion.status == CompletionStatus.COMPLETED,
        )
        stmt = (
            select(Task)
            .options(selectinload(Task.course))
        )
        if completed_only:
            stmt = stmt.where(Task.id.in_(completed_task_ids))
        else:
            stmt = stmt.where(
                or_(
                    and_(
                        Task.status == TaskStatus.ACTIVE,
                        or_(
                            and_(
                                Task.assignment_scope == TaskAssignmentScope.ALL_STUDENTS,
                                Task.course_id.in_(course_ids),
                            ),
                            and_(
                                Task.assignment_scope == TaskAssignmentScope.SELECTED_STUDENTS,
                                Task.id.in_(
                                    select(TaskRecipient.task_id).where(
                                        TaskRecipient.student_id == student_id
                                    )
                                ),
                            ),
                        ),
                    ),
                    Task.id.in_(completed_task_ids),
                )
            )
        if course_id:
            stmt = stmt.where(Task.course_id == course_id)
        stmt = stmt.order_by(Task.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def student_has_completed_tasks_in_course(
        self, student_id: uuid.UUID, course_id: uuid.UUID
    ) -> bool:
        stmt = (
            select(TaskCompletion.id)
            .join(Task, Task.id == TaskCompletion.task_id)
            .where(
                TaskCompletion.student_id == student_id,
                TaskCompletion.status == CompletionStatus.COMPLETED,
                Task.course_id == course_id,
            )
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none() is not None

    async def create(self, task: Task) -> Task:
        self.db.add(task)
        await self.db.commit()
        created_task = await self.get_by_id(task.id)
        if created_task is None:
            raise RuntimeError(f"Created task {task.id} could not be reloaded")
        return created_task

    async def update(self, task: Task) -> Task:
        await self.db.commit()
        await self.db.refresh(task)
        return task

    # Task completions
    async def get_completion(self, task_id: uuid.UUID, student_id: uuid.UUID) -> Optional[TaskCompletion]:
        stmt = select(TaskCompletion).options(selectinload(TaskCompletion.task)).where(
            TaskCompletion.task_id == task_id,
            TaskCompletion.student_id == student_id,
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_completion_by_id(self, completion_id: uuid.UUID) -> Optional[TaskCompletion]:
        stmt = (
            select(TaskCompletion)
            .options(
                selectinload(TaskCompletion.task).selectinload(Task.course),
                selectinload(TaskCompletion.student),
                selectinload(TaskCompletion.reviewer),
            )
            .where(TaskCompletion.id == completion_id)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def count_task_completions(self, task_id: uuid.UUID) -> int:
        stmt = select(func.count(TaskCompletion.id)).where(TaskCompletion.task_id == task_id)
        res = await self.db.execute(stmt)
        return res.scalar_one()

    async def create_or_ignore_exam_completion(self, task: Task, student_id: uuid.UUID) -> Optional[TaskCompletion]:
        """
        Idempotent completion for exam tasks.
        If completion already exists, does nothing and returns existing or None.
        """
        existing = await self.get_completion(task.id, student_id)
        if existing:
            return existing

        now = datetime.now(timezone.utc)
        completion = TaskCompletion(
            task_id=task.id,
            student_id=student_id,
            status=CompletionStatus.COMPLETED,
            points_awarded=task.points,
            submitted_at=now,
            completed_at=now,
        )
        self.db.add(completion)
        # We don't commit here so the caller can include it in the grading transaction
        await self.db.flush()
        return completion

    async def list_pending_reviews(
        self,
        course_ids: Optional[List[uuid.UUID]] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> List[TaskCompletion]:
        stmt = (
            select(TaskCompletion)
            .join(Task, Task.id == TaskCompletion.task_id)
            .options(
                selectinload(TaskCompletion.task).selectinload(Task.course),
                selectinload(TaskCompletion.student),
            )
            .where(TaskCompletion.status == CompletionStatus.PENDING_REVIEW)
        )
        if course_ids is not None and created_by is not None:
            stmt = stmt.where(
                or_(Task.course_id.in_(course_ids), Task.created_by == created_by)
            )
        elif course_ids is not None:
            stmt = stmt.where(Task.course_id.in_(course_ids))
        elif created_by is not None:
            stmt = stmt.where(Task.created_by == created_by)

        stmt = stmt.order_by(TaskCompletion.submitted_at.asc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def list_student_completions(self, student_id: uuid.UUID) -> List[TaskCompletion]:
        stmt = (
            select(TaskCompletion)
            .options(selectinload(TaskCompletion.task).selectinload(Task.course))
            .where(TaskCompletion.student_id == student_id)
            .order_by(TaskCompletion.submitted_at.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def list_student_video_progress(
        self, student_id: uuid.UUID, task_ids: List[uuid.UUID]
    ) -> List[TaskVideoProgress]:
        if not task_ids:
            return []
        stmt = select(TaskVideoProgress).where(
            TaskVideoProgress.student_id == student_id,
            TaskVideoProgress.task_id.in_(task_ids),
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_student_points_summary(self, student_id: uuid.UUID) -> Tuple[int, int, Optional[datetime]]:
        """
        Returns (total_points, tasks_completed, last_completed_at)
        Only considers status = 'completed'.
        """
        stmt = select(
            func.coalesce(func.sum(TaskCompletion.points_awarded), 0),
            func.count(TaskCompletion.id),
            func.max(TaskCompletion.completed_at),
        ).where(
            TaskCompletion.student_id == student_id,
            TaskCompletion.status == CompletionStatus.COMPLETED,
        )
        res = await self.db.execute(stmt)
        row = res.one()
        return int(row[0]), int(row[1]), row[2]

    async def get_student_ranking_summary(
        self,
        student_id: uuid.UUID,
        course_id: uuid.UUID,
    ) -> Optional[Tuple[int, int, int]]:
        summary = (
            select(
                TaskCompletion.student_id.label("student_id"),
                func.sum(TaskCompletion.points_awarded).label("points"),
                func.count(TaskCompletion.id).label("tasks_completed"),
                func.max(TaskCompletion.completed_at).label("last_completed_at"),
            )
            .join(User, User.id == TaskCompletion.student_id)
            .join(Task, Task.id == TaskCompletion.task_id)
            .where(
                TaskCompletion.status == CompletionStatus.COMPLETED,
                User.status == "active",
                Task.course_id == course_id,
            )
            .group_by(TaskCompletion.student_id)
            .having(func.sum(TaskCompletion.points_awarded) > 0)
            .subquery()
        )
        ranked = (
            select(
                summary.c.student_id,
                func.row_number()
                .over(
                    order_by=(
                        summary.c.points.desc(),
                        summary.c.last_completed_at.asc(),
                        summary.c.student_id.asc(),
                    )
                )
                .label("rank"),
                summary.c.points,
                summary.c.tasks_completed,
            )
            .subquery()
        )
        row = (
            await self.db.execute(
                select(ranked.c.rank, ranked.c.points, ranked.c.tasks_completed).where(
                    ranked.c.student_id == student_id
                )
            )
        ).one_or_none()
        if row is None:
            return None
        return int(row.rank), int(row.points), int(row.tasks_completed)

    async def get_student_points_summaries(
        self, student_ids: List[uuid.UUID]
    ) -> dict[uuid.UUID, Tuple[str, Optional[str], int, int]]:
        if not student_ids:
            return {}

        stmt = (
            select(
                User.id,
                User.full_name,
                User.avatar_url,
                func.coalesce(func.sum(TaskCompletion.points_awarded), 0),
                func.count(TaskCompletion.id),
            )
            .outerjoin(
                TaskCompletion,
                and_(
                    TaskCompletion.student_id == User.id,
                    TaskCompletion.status == CompletionStatus.COMPLETED,
                ),
            )
            .where(User.id.in_(student_ids), User.status == "active")
            .group_by(User.id, User.full_name, User.avatar_url)
        )
        rows = (await self.db.execute(stmt)).all()
        return {
            student_id: (name, avatar, int(points), int(tasks_completed))
            for student_id, name, avatar, points, tasks_completed in rows
        }

    async def get_top_students_sql(self, course_id: Optional[uuid.UUID] = None, limit: int = 4) -> List[Tuple[uuid.UUID, str, Optional[str], int, int, datetime]]:
        """
        Database fallback for leaderboard:
        Returns list of (student_id, name, avatar_url, points, tasks_completed, last_completed_at)
        """
        stmt = (
            select(
                TaskCompletion.student_id,
                User.full_name,
                User.avatar_url,
                func.sum(TaskCompletion.points_awarded).label("points"),
                func.count(TaskCompletion.id).label("tasks_completed"),
                func.max(TaskCompletion.completed_at).label("last_completed_at"),
            )
            .join(User, User.id == TaskCompletion.student_id)
            .join(Task, Task.id == TaskCompletion.task_id)
            .where(
                TaskCompletion.status == CompletionStatus.COMPLETED,
                User.status == "active",
            )
        )
        if course_id:
            stmt = stmt.where(Task.course_id == course_id)

        stmt = (
            stmt.group_by(TaskCompletion.student_id, User.full_name, User.avatar_url)
            .having(func.sum(TaskCompletion.points_awarded) > 0)
            .order_by(
                func.sum(TaskCompletion.points_awarded).desc(),
                func.max(TaskCompletion.completed_at).asc(),
            )
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.all())
