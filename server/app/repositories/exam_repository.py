import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models.exam import AttemptAnswer, AttemptStatus, Exam, ExamAttempt, ExamStatus, Question, QuestionOption


class ExamRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, exam_id: uuid.UUID) -> Optional[Exam]:
        stmt = (
            select(Exam)
            .options(
                selectinload(Exam.course),
                selectinload(Exam.questions).selectinload(Question.options),
                selectinload(Exam.task),
            )
            .where(Exam.id == exam_id)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_exams(
        self,
        course_id: Optional[uuid.UUID] = None,
        status: Optional[ExamStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Exam], int]:
        stmt = select(Exam).options(selectinload(Exam.course), selectinload(Exam.task))
        count_stmt = select(func.count(Exam.id))

        if course_id:
            stmt = stmt.where(Exam.course_id == course_id)
            count_stmt = count_stmt.where(Exam.course_id == course_id)
        if status:
            stmt = stmt.where(Exam.status == status)
            count_stmt = count_stmt.where(Exam.status == status)

        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = stmt.order_by(Exam.start_at.desc()).offset((page - 1) * page_size).limit(page_size)
        res = await self.db.execute(stmt)
        return list(res.scalars().all()), total

    async def create(self, exam: Exam) -> Exam:
        self.db.add(exam)
        await self.db.commit()
        await self.db.refresh(exam)
        return exam

    async def update(self, exam: Exam) -> Exam:
        await self.db.commit()
        await self.db.refresh(exam)
        return exam

    async def add_question(self, question: Question) -> Question:
        self.db.add(question)
        await self.db.commit()
        await self.db.refresh(question)
        return question

    async def get_attempt(self, attempt_id: uuid.UUID) -> Optional[ExamAttempt]:
        stmt = (
            select(ExamAttempt)
            .options(
                selectinload(ExamAttempt.exam).selectinload(Exam.questions).selectinload(Question.options),
                selectinload(ExamAttempt.student),
                selectinload(ExamAttempt.answers),
            )
            .where(ExamAttempt.id == attempt_id)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_active_attempt_for_student(self, student_id: uuid.UUID) -> Optional[ExamAttempt]:
        stmt = (
            select(ExamAttempt)
            .options(
                selectinload(ExamAttempt.exam).selectinload(Exam.questions).selectinload(Question.options),
            )
            .where(
                ExamAttempt.student_id == student_id,
                ExamAttempt.status == AttemptStatus.IN_PROGRESS,
                ExamAttempt.expires_at > func.now(),
            )
            .limit(1)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def count_attempts(self, exam_id: uuid.UUID, student_id: uuid.UUID) -> int:
        stmt = select(func.count(ExamAttempt.id)).where(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.student_id == student_id,
        )
        res = await self.db.execute(stmt)
        return res.scalar_one()

    async def count_reexam_approvals(self, exam_id: uuid.UUID, student_id: uuid.UUID) -> int:
        stmt = select(func.count(ExamAttempt.id)).where(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.student_id == student_id,
            ExamAttempt.reexam_approved_at.is_not(None),
        )
        res = await self.db.execute(stmt)
        return res.scalar_one()

    async def list_pending_integrity_reviews(self) -> List[ExamAttempt]:
        stmt = (
            select(ExamAttempt)
            .options(
                selectinload(ExamAttempt.exam).selectinload(Exam.course),
                selectinload(ExamAttempt.student),
            )
            .where(
                ExamAttempt.integrity_violation.is_(True),
                ExamAttempt.reexam_approved_at.is_(None),
            )
            .order_by(ExamAttempt.integrity_flagged_at.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create_attempt(self, attempt: ExamAttempt) -> ExamAttempt:
        self.db.add(attempt)
        await self.db.commit()
        await self.db.refresh(attempt)
        return attempt

    async def update_attempt(self, attempt: ExamAttempt) -> ExamAttempt:
        await self.db.commit()
        await self.db.refresh(attempt)
        return attempt

    async def upsert_answer(self, attempt_id: uuid.UUID, question_id: uuid.UUID, selected_option_id: Optional[uuid.UUID]) -> AttemptAnswer:
        stmt = select(AttemptAnswer).where(
            AttemptAnswer.attempt_id == attempt_id,
            AttemptAnswer.question_id == question_id,
        )
        res = await self.db.execute(stmt)
        ans = res.scalar_one_or_none()
        if ans:
            ans.selected_option_id = selected_option_id
            ans.answered_at = datetime.now(timezone.utc)
        else:
            ans = AttemptAnswer(
                attempt_id=attempt_id,
                question_id=question_id,
                selected_option_id=selected_option_id,
                answered_at=datetime.now(timezone.utc),
            )
            self.db.add(ans)
        await self.db.commit()
        await self.db.refresh(ans)
        return ans

    async def list_expired_in_progress_attempts(self) -> List[ExamAttempt]:
        stmt = select(ExamAttempt).where(
            ExamAttempt.status == AttemptStatus.IN_PROGRESS,
            ExamAttempt.expires_at <= func.now(),
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
