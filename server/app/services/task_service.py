import uuid
import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from urllib.parse import parse_qs, urlparse
from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.db.models.course import Course, Enrollment, EnrollmentStatus
from app.db.models.task import (
    CompletionStatus,
    Task,
    TaskAssignmentScope,
    TaskCompletion,
    TaskRecipient,
    TaskStatus,
    TaskType,
    TaskVerification,
    TaskResourceType,
    TaskVideoProgress,
)
from app.db.models.user import User, UserRole, UserStatus
from app.repositories.audit_repository import AuditRepository
from app.repositories.course_repository import CourseRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.task import StudentPointsResponse, TaskCreate, TaskPointsHistoryItem, TaskUpdate
from app.services.ranking_service import RankingService


class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.task_repo = TaskRepository(db)
        self.course_repo = CourseRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditRepository(db)
        self.ranking_service = RankingService(db)

    async def create_assignment_task(self, data: TaskCreate, creator: User) -> Task:
        if data.resource_type == TaskResourceType.VIDEO and data.resource_url:
            parsed_url = urlparse(str(data.resource_url))
            host = (parsed_url.hostname or "").lower()
            path_parts = [part for part in parsed_url.path.split("/") if part]
            video_id = None
            if host == "youtu.be" and path_parts:
                video_id = path_parts[0]
            elif host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
                if parsed_url.path == "/watch":
                    video_id = parse_qs(parsed_url.query).get("v", [None])[0]
                elif len(path_parts) > 1 and path_parts[0] in {"embed", "shorts", "live"}:
                    video_id = path_parts[1]
            if not video_id or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Video tasks require a valid YouTube video URL",
                )

        course = await self.course_repo.get_by_id(data.course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        if creator.role == UserRole.TEACHER and not await self.course_repo.is_teacher_assigned(course.id, creator.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only create tasks in a course assigned to you.",
            )

        if data.assignment_scope == TaskAssignmentScope.SELECTED_STUDENTS:
            target_ids = set(data.target_student_ids)
            if len(target_ids) != len(data.target_student_ids):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="A student can only be selected once",
                )
            students_stmt = (
                select(User.id)
                .where(
                    User.id.in_(target_ids),
                    User.role == UserRole.STUDENT,
                    User.status == UserStatus.ACTIVE,
                )
            )
            active_student_ids = set((await self.db.execute(students_stmt)).scalars().all())
            if active_student_ids != target_ids:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Every selected student must be an active student",
                )

        task = Task(
            course_id=data.course_id,
            created_by=creator.id,
            type=TaskType.ASSIGNMENT,
            exam_id=None,
            title=data.title,
            description=data.description,
            points=data.points,
            verification=TaskVerification.TEACHER_APPROVAL,
            due_at=data.due_at,
            resource_type=data.resource_type,
            resource_url=str(data.resource_url) if data.resource_url else None,
            assignment_scope=data.assignment_scope,
            status=TaskStatus.ACTIVE,
        )
        if data.assignment_scope == TaskAssignmentScope.SELECTED_STUDENTS:
            task.recipients = [
                TaskRecipient(student_id=student_id)
                for student_id in data.target_student_ids
            ]
        return await self.task_repo.create(task)

    async def student_can_access_task(self, task: Task, student_id: uuid.UUID) -> bool:
        if task.assignment_scope == TaskAssignmentScope.SELECTED_STUDENTS:
            recipient_stmt = select(TaskRecipient.student_id).where(
                TaskRecipient.task_id == task.id,
                TaskRecipient.student_id == student_id,
            )
            return (await self.db.execute(recipient_stmt)).scalar_one_or_none() is not None

        enrollment_stmt = select(Enrollment.student_id).where(
            Enrollment.student_id == student_id,
            Enrollment.course_id == task.course_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
        return (await self.db.execute(enrollment_stmt)).scalar_one_or_none() is not None

    async def update_task(self, task_id: uuid.UUID, data: TaskUpdate, user: User) -> Task:
        fields = data.model_fields_set
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        course = await self.course_repo.get_by_id(task.course_id)
        if user.role == UserRole.TEACHER and task.created_by != user.id and course and not await self.course_repo.is_teacher_assigned(course.id, user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot edit tasks from another teacher's course")

        if task.type == TaskType.EXAM and fields.intersection({"course_id", "resource_type", "resource_url", "assignment_scope", "target_student_ids"}):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam course, resource, and assignment settings are managed by the exam.",
            )

        if "course_id" in data.model_fields_set:
            if data.course_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="A course must be selected.",
                )
            target_course = await self.course_repo.get_by_id(data.course_id)
            if not target_course:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
            if user.role == UserRole.TEACHER and not await self.course_repo.is_teacher_assigned(target_course.id, user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only move a task to a course assigned to you.",
                )
            task.course_id = target_course.id
            task.course = target_course

        if data.title is not None:
            task.title = data.title
        if "description" in fields:
            task.description = data.description
        if "points" in fields and data.points is not None:
            task.points = data.points
        if "due_at" in fields:
            task.due_at = data.due_at

        if fields.intersection({"resource_type", "resource_url"}):
            resource_type = data.resource_type if "resource_type" in fields else task.resource_type
            resource_url = (
                str(data.resource_url) if data.resource_url else None
            ) if "resource_url" in fields else task.resource_url
            if (resource_type is None) != (resource_url is None):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Resource type and resource URL must be provided together, or both cleared.",
                )
            if resource_type == TaskResourceType.VIDEO and resource_url:
                parsed_url = urlparse(resource_url)
                host = (parsed_url.hostname or "").lower()
                path_parts = [part for part in parsed_url.path.split("/") if part]
                video_id = None
                if host == "youtu.be" and path_parts:
                    video_id = path_parts[0]
                elif host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
                    if parsed_url.path == "/watch":
                        video_id = parse_qs(parsed_url.query).get("v", [None])[0]
                    elif len(path_parts) > 1 and path_parts[0] in {"embed", "shorts", "live"}:
                        video_id = path_parts[1]
                if not video_id or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail="Video tasks require a valid YouTube video URL",
                    )
            if resource_url != task.resource_url:
                await self.db.execute(
                    delete(TaskVideoProgress).where(TaskVideoProgress.task_id == task.id)
                )
            task.resource_type = resource_type
            task.resource_url = resource_url

        if fields.intersection({"assignment_scope", "target_student_ids"}):
            assignment_scope = data.assignment_scope if "assignment_scope" in fields else task.assignment_scope
            if assignment_scope is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Assignment scope cannot be empty.",
                )
            current_recipient_ids = list((await self.db.scalars(
                select(TaskRecipient.student_id).where(TaskRecipient.task_id == task.id)
            )).all())
            target_ids = data.target_student_ids if "target_student_ids" in fields else current_recipient_ids
            target_ids = target_ids or []
            if assignment_scope == TaskAssignmentScope.SELECTED_STUDENTS and not target_ids:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Select at least one student for an individually assigned task",
                )
            if assignment_scope == TaskAssignmentScope.ALL_STUDENTS and target_ids:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Selected students cannot be supplied when assigning to all students",
                )
            if len(set(target_ids)) != len(target_ids):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="A student can only be selected once",
                )
            newly_selected_ids = set(target_ids) - set(current_recipient_ids)
            if newly_selected_ids:
                active_student_ids = set((await self.db.scalars(
                    select(User.id).where(
                        User.id.in_(newly_selected_ids),
                        User.role == UserRole.STUDENT,
                        User.status == UserStatus.ACTIVE,
                    )
                )).all())
                if active_student_ids != newly_selected_ids:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail="Every selected student must be an active student",
                    )
            await self.db.execute(delete(TaskRecipient).where(TaskRecipient.task_id == task.id))
            if assignment_scope == TaskAssignmentScope.SELECTED_STUDENTS:
                self.db.add_all(
                    TaskRecipient(task_id=task.id, student_id=student_id)
                    for student_id in target_ids
                )
            task.assignment_scope = assignment_scope

        return await self.task_repo.update(task)

    async def archive_task(self, task_id: uuid.UUID, user: User) -> Task:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        course = await self.course_repo.get_by_id(task.course_id)
        if user.role == UserRole.TEACHER and task.created_by != user.id and course and not await self.course_repo.is_teacher_assigned(course.id, user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot archive tasks from another teacher's course")

        task.status = TaskStatus.ARCHIVED
        return await self.task_repo.update(task)

    async def submit_assignment(self, task_id: uuid.UUID, student_id: uuid.UUID, note: Optional[str], url: Optional[str]) -> TaskCompletion:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        if task.type != TaskType.ASSIGNMENT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only assignment tasks can be submitted manually")
        if task.status != TaskStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This task is not active")
        if not await self.student_can_access_task(task, student_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        if task.resource_type == TaskResourceType.VIDEO:
            progress_stmt = select(TaskVideoProgress.progress_percent).where(
                TaskVideoProgress.task_id == task_id,
                TaskVideoProgress.student_id == student_id,
            )
            progress = (await self.db.execute(progress_stmt)).scalar_one_or_none()
            if progress is None or progress < 80:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Watch at least 80% of the video before submitting this task",
                )

        completion = await self.task_repo.get_completion(task_id, student_id)
        now = datetime.now(timezone.utc)
        is_auto_graded = task.verification == TaskVerification.AUTO
        if completion:
            if completion.status == CompletionStatus.COMPLETED:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task is already completed")
            completion.submission_note = note
            completion.submission_url = url
            completion.status = (
                CompletionStatus.COMPLETED if is_auto_graded else CompletionStatus.PENDING_REVIEW
            )
            completion.points_awarded = task.points if is_auto_graded else 0
            completion.submitted_at = now
            completion.completed_at = now if is_auto_graded else None
        else:
            completion = TaskCompletion(
                task_id=task_id,
                student_id=student_id,
                status=CompletionStatus.COMPLETED if is_auto_graded else CompletionStatus.PENDING_REVIEW,
                submission_note=note,
                submission_url=url,
                points_awarded=task.points if is_auto_graded else 0,
                submitted_at=now,
                completed_at=now if is_auto_graded else None,
            )
            self.db.add(completion)

        await self.db.commit()
        await self.db.refresh(completion)
        if is_auto_graded:
            await self.ranking_service.refresh_student(student_id)
        return completion

    async def update_video_progress(
        self,
        task_id: uuid.UUID,
        student_id: uuid.UUID,
        progress_percent: float,
        video_duration_seconds: float,
    ) -> float:
        task = await self.task_repo.get_by_id(task_id)
        if not task or task.resource_type != TaskResourceType.VIDEO:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video task not found")
        if task.status != TaskStatus.ACTIVE or not await self.student_can_access_task(task, student_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video task not found")

        completion = await self.task_repo.get_completion(task_id, student_id)
        if completion and completion.status in {
            CompletionStatus.PENDING_REVIEW,
            CompletionStatus.COMPLETED,
        }:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Video progress cannot be changed after submission",
            )

        progress_stmt = select(TaskVideoProgress).where(
            TaskVideoProgress.task_id == task_id,
            TaskVideoProgress.student_id == student_id,
        )
        progress = (await self.db.execute(progress_stmt)).scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if progress:
            last_updated = progress.updated_at
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)
            elapsed_seconds = max(0.0, (now - last_updated).total_seconds())
            max_increment = elapsed_seconds / video_duration_seconds * 100 * 2.25
            progress.progress_percent = max(
                progress.progress_percent,
                min(progress_percent, progress.progress_percent + max_increment),
            )
            progress.updated_at = now
        else:
            progress = TaskVideoProgress(
                task_id=task_id,
                student_id=student_id,
                progress_percent=0,
                updated_at=now,
            )
            self.db.add(progress)

        await self.db.commit()
        await self.db.refresh(progress)
        return progress.progress_percent

    async def approve_assignment(self, completion_id: uuid.UUID, reviewer: User, review_note: Optional[str]) -> TaskCompletion:
        completion = await self.task_repo.get_completion_by_id(completion_id)
        if not completion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task completion record not found")

        task = completion.task
        course = await self.course_repo.get_by_id(task.course_id)
        if reviewer.role == UserRole.TEACHER and task.created_by != reviewer.id and course and not await self.course_repo.is_teacher_assigned(course.id, reviewer.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only approve tasks for your own courses")

        now = datetime.now(timezone.utc)
        completion.status = CompletionStatus.COMPLETED
        completion.points_awarded = task.points
        completion.completed_at = now
        completion.reviewed_by = reviewer.id
        completion.reviewed_at = now
        completion.review_note = review_note

        await self.db.commit()
        await self.db.refresh(completion)

        # Refresh student ranking immediately
        await self.ranking_service.refresh_student(completion.student_id)
        return completion

    async def reject_assignment(self, completion_id: uuid.UUID, reviewer: User, review_note: Optional[str]) -> TaskCompletion:
        completion = await self.task_repo.get_completion_by_id(completion_id)
        if not completion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task completion record not found")

        task = completion.task
        course = await self.course_repo.get_by_id(task.course_id)
        if reviewer.role == UserRole.TEACHER and task.created_by != reviewer.id and course and not await self.course_repo.is_teacher_assigned(course.id, reviewer.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only review tasks for your own courses")

        now = datetime.now(timezone.utc)
        completion.status = CompletionStatus.REJECTED
        completion.points_awarded = 0
        completion.reviewed_by = reviewer.id
        completion.reviewed_at = now
        completion.review_note = review_note

        await self.db.commit()
        await self.db.refresh(completion)
        return completion

    async def complete_exam_task_if_passed(self, exam_id: uuid.UUID, student_id: uuid.UUID) -> int:
        """
        Called inside the exam grading process.
        Returns the points awarded (0 if already completed or exam has no points).
        """
        task = await self.task_repo.get_by_exam_id(exam_id)
        if not task or task.points <= 0 or task.status != TaskStatus.ACTIVE:
            return 0

        existing = await self.task_repo.get_completion(task.id, student_id)
        if existing and existing.status == CompletionStatus.COMPLETED:
            return 0  # Already awarded once

        now = datetime.now(timezone.utc)
        if existing:
            existing.status = CompletionStatus.COMPLETED
            existing.points_awarded = task.points
            existing.completed_at = now
        else:
            comp = TaskCompletion(
                task_id=task.id,
                student_id=student_id,
                status=CompletionStatus.COMPLETED,
                points_awarded=task.points,
                submitted_at=now,
                completed_at=now,
            )
            self.db.add(comp)

        # Let the caller commit the transaction
        return task.points

    async def revoke_completion(self, completion_id: uuid.UUID, admin: User, reason: Optional[str]) -> TaskCompletion:
        if admin.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can revoke task completions")

        completion = await self.task_repo.get_completion_by_id(completion_id)
        if not completion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Completion not found")

        now = datetime.now(timezone.utc)
        old_points = completion.points_awarded
        completion.status = CompletionStatus.REVOKED
        completion.points_awarded = 0
        completion.revoked_by = admin.id
        completion.revoked_at = now

        await self.audit_repo.log(
            actor_id=admin.id,
            action="task_completion.revoked",
            entity_type="task_completion",
            entity_id=str(completion.id),
            metadata={"student_id": str(completion.student_id), "revoked_points": old_points, "reason": reason},
        )

        await self.db.commit()
        await self.db.refresh(completion)

        # Refresh student ranking immediately to remove points
        await self.ranking_service.refresh_student(completion.student_id)
        return completion

    async def get_student_points(self, student_id: uuid.UUID) -> StudentPointsResponse:
        total_pts, tasks_cnt, _ = await self.task_repo.get_student_points_summary(student_id)
        rank_resp = await self.ranking_service.get_student_rank(student_id)

        completions = await self.task_repo.list_student_completions(student_id)
        history: List[TaskPointsHistoryItem] = []
        for c in completions:
            if c.status == CompletionStatus.COMPLETED and c.completed_at:
                history.append(
                    TaskPointsHistoryItem(
                        completion_id=c.id,
                        task_id=c.task_id,
                        task_title=c.task.title if c.task else "Task",
                        course_title=c.task.course.title if c.task and c.task.course else "Course",
                        points=c.points_awarded,
                        completed_at=c.completed_at,
                    )
                )

        return StudentPointsResponse(
            total_points=total_pts,
            tasks_completed=tasks_cnt,
            rank=rank_resp.rank,
            history=history,
        )
