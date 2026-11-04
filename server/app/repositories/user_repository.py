import uuid
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.user import (
    StudentProfile,
    TeacherProfile,
    User,
    UserRole,
    UserStatus,
)


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = (
            select(User)
            .options(
                selectinload(User.student_profile).selectinload(StudentProfile.department),
                selectinload(User.teacher_profile).selectinload(TeacherProfile.department),
            )
            .where(User.id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_clerk_id(self, clerk_user_id: str) -> Optional[User]:
        stmt = (
            select(User)
            .options(
                selectinload(User.student_profile).selectinload(StudentProfile.department),
                selectinload(User.teacher_profile).selectinload(TeacherProfile.department),
            )
            .where(User.clerk_user_id == clerk_user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = (
            select(User)
            .options(
                selectinload(User.student_profile).selectinload(StudentProfile.department),
                selectinload(User.teacher_profile).selectinload(TeacherProfile.department),
            )
            .where(User.email == email)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_users(
        self,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[User], int]:
        stmt = select(User).options(
            selectinload(User.student_profile).selectinload(StudentProfile.department),
            selectinload(User.teacher_profile).selectinload(TeacherProfile.department),
        )
        count_stmt = select(func.count(User.id))

        if role:
            stmt = stmt.where(User.role == role)
            count_stmt = count_stmt.where(User.role == role)
        if status:
            stmt = stmt.where(User.status == status)
            count_stmt = count_stmt.where(User.status == status)
        if search:
            term = f"%{search.lower()}%"
            filter_cond = func.lower(User.full_name).like(term) | func.lower(User.email).like(term)
            stmt = stmt.where(filter_cond)
            count_stmt = count_stmt.where(filter_cond)

        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        res = await self.db.execute(stmt)
        return list(res.scalars().all()), total

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        return (await self.get_by_id(user.id)) or user

    async def update(self, user: User) -> User:
        await self.db.commit()
        return (await self.get_by_id(user.id)) or user

    async def get_student_by_qr_token(self, qr_token: str) -> Optional[StudentProfile]:
        stmt = (
            select(StudentProfile)
            .options(
                selectinload(StudentProfile.user),
                selectinload(StudentProfile.department),
            )
            .where(StudentProfile.qr_token == qr_token)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def next_student_code(self, year: int) -> str:
        prefix = f"SBU-{year}-"
        result = await self.db.execute(
            select(StudentProfile.student_code).where(
                StudentProfile.student_code.like(f"{prefix}%")
            )
        )
        numbers = [
            int(code[len(prefix):])
            for code in result.scalars()
            if code.startswith(prefix) and code[len(prefix):].isdigit()
        ]
        return f"{prefix}{max(numbers, default=0) + 1:04d}"

    async def get_user_stats(self) -> dict:
        stmt = select(User.role, func.count(User.id)).group_by(User.role)
        res = await self.db.execute(stmt)
        role_counts = dict(res.all())
        students = role_counts.get(UserRole.STUDENT, 0)
        teachers = role_counts.get(UserRole.TEACHER, 0)
        admins = role_counts.get(UserRole.ADMIN, 0)
        total = students + teachers + admins
        return {
            "total": total,
            "students": students,
            "teachers": teachers,
            "admins": admins,
        }
