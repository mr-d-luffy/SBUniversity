import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models.course import Course
from app.db.models.exam import Exam
from app.db.models.result import Result


class ResultRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, result_id: uuid.UUID) -> Optional[Result]:
        stmt = (
            select(Result)
            .options(
                selectinload(Result.exam).selectinload(Exam.course),
                selectinload(Result.student),
                selectinload(Result.attempt),
            )
            .where(Result.id == result_id)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_attempt_id(self, attempt_id: uuid.UUID) -> Optional[Result]:
        stmt = (
            select(Result)
            .options(
                selectinload(Result.exam).selectinload(Exam.course),
                selectinload(Result.student),
            )
            .where(Result.attempt_id == attempt_id)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_results(
        self,
        student_id: Optional[uuid.UUID] = None,
        exam_id: Optional[uuid.UUID] = None,
        course_ids: Optional[List[uuid.UUID]] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Result], int]:
        stmt = select(Result).options(selectinload(Result.exam).selectinload(Exam.course), selectinload(Result.student))
        count_stmt = select(func.count(Result.id))

        if student_id:
            stmt = stmt.where(Result.student_id == student_id)
            count_stmt = count_stmt.where(Result.student_id == student_id)
        if exam_id:
            stmt = stmt.where(Result.exam_id == exam_id)
            count_stmt = count_stmt.where(Result.exam_id == exam_id)
        if course_ids is not None:
            allowed_exam_ids = select(Exam.id).where(Exam.course_id.in_(course_ids))
            stmt = stmt.where(Result.exam_id.in_(allowed_exam_ids))
            count_stmt = count_stmt.where(Result.exam_id.in_(allowed_exam_ids))

        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = stmt.order_by(Result.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        res = await self.db.execute(stmt)
        return list(res.scalars().all()), total

    async def count_passed_exams_for_student_in_course(self, student_id: uuid.UUID, course_id: uuid.UUID) -> int:
        stmt = (
            select(func.count(func.distinct(Result.exam_id)))
            .join(Exam, Exam.id == Result.exam_id)
            .where(
                Result.student_id == student_id,
                Exam.course_id == course_id,
                Result.passed == True,
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one()

    async def calculate_exam_rank(self, exam_id: uuid.UUID, score: float, time_taken_sec: int) -> int:
        # Number of results with higher score, or same score and lower time + 1
        stmt = select(func.count(Result.id)).where(
            Result.exam_id == exam_id,
            (Result.score > score) | ((Result.score == score) & (Result.time_taken_sec < time_taken_sec)),
        )
        res = await self.db.execute(stmt)
        return res.scalar_one() + 1

    async def create(self, result: Result) -> Result:
        self.db.add(result)
        await self.db.commit()
        await self.db.refresh(result)
        return result

    async def update(self, result: Result) -> Result:
        await self.db.commit()
        await self.db.refresh(result)
        return result
