import uuid
from datetime import datetime, timezone
import secrets

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.course import (
    Course,
    CourseKeyRequest,
    CourseKeyRequestStatus,
    CourseUnlock,
    Enrollment,
    EnrollmentStatus,
)
from app.db.models.user import User


async def unlocked_course_ids(db: AsyncSession, student_id: uuid.UUID) -> set[uuid.UUID]:
    return set(
        (
            await db.scalars(
                select(CourseUnlock.course_id).where(
                    CourseUnlock.student_id == student_id
                )
            )
        ).all()
    )


async def is_course_unlocked(
    db: AsyncSession, student_id: uuid.UUID, course_id: uuid.UUID
) -> bool:
    return (
        await db.scalar(
            select(CourseUnlock.id).where(
                CourseUnlock.student_id == student_id,
                CourseUnlock.course_id == course_id,
            )
        )
    ) is not None


class CourseAccessService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def request_key(
        self, course_id: uuid.UUID, student: User
    ) -> CourseKeyRequest:
        course = await self.db.get(Course, course_id)
        if course is None or not course.is_published:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Published course not found",
            )
        if await is_course_unlocked(self.db, student.id, course_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This course is already unlocked.",
            )
        pending = await self.db.scalar(
            select(CourseKeyRequest.id).where(
                CourseKeyRequest.student_id == student.id,
                CourseKeyRequest.course_id == course_id,
                CourseKeyRequest.status == CourseKeyRequestStatus.PENDING,
            )
        )
        if pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A key request for this course is already awaiting review.",
            )

        request = CourseKeyRequest(
            student_id=student.id,
            course_id=course_id,
            status=CourseKeyRequestStatus.PENDING,
        )
        self.db.add(request)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A key request for this course is already awaiting review.",
            ) from exc
        await self.db.refresh(request)
        return request

    async def list_student_requests(
        self, student_id: uuid.UUID
    ) -> list[tuple[CourseKeyRequest, Course]]:
        rows = await self.db.execute(
            select(CourseKeyRequest, Course)
            .join(Course, Course.id == CourseKeyRequest.course_id)
            .where(CourseKeyRequest.student_id == student_id)
            .order_by(CourseKeyRequest.requested_at.desc())
        )
        return list(rows.all())

    async def list_admin_requests(
        self,
    ) -> list[tuple[CourseKeyRequest, Course, User]]:
        rows = await self.db.execute(
            select(CourseKeyRequest, Course, User)
            .join(Course, Course.id == CourseKeyRequest.course_id)
            .join(User, User.id == CourseKeyRequest.student_id)
            .order_by(CourseKeyRequest.requested_at.desc())
        )
        return list(rows.all())

    async def approve_request(
        self, request_id: uuid.UUID, admin: User
    ) -> CourseKeyRequest:
        request = await self.db.scalar(
            select(CourseKeyRequest)
            .where(CourseKeyRequest.id == request_id)
            .with_for_update()
        )
        if request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Key request not found.",
            )
        if request.status != CourseKeyRequestStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending key requests can be approved.",
            )

        request.access_key = self._generate_unique_key()
        request.status = CourseKeyRequestStatus.APPROVED
        request.reviewed_at = datetime.now(timezone.utc)
        request.reviewed_by = admin.id
        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def reject_request(
        self, request_id: uuid.UUID, admin: User
    ) -> CourseKeyRequest:
        request = await self.db.scalar(
            select(CourseKeyRequest)
            .where(CourseKeyRequest.id == request_id)
            .with_for_update()
        )
        if request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Key request not found.",
            )
        if request.status != CourseKeyRequestStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending key requests can be rejected.",
            )
        request.status = CourseKeyRequestStatus.REJECTED
        request.reviewed_at = datetime.now(timezone.utc)
        request.reviewed_by = admin.id
        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def activate_key(self, key: str, student: User) -> CourseUnlock:
        request = await self.db.scalar(
            select(CourseKeyRequest).where(CourseKeyRequest.access_key == key)
        )
        if (
            request is None
            or request.student_id != student.id
            or request.status != CourseKeyRequestStatus.APPROVED
            or not request.access_key
            or not secrets.compare_digest(request.access_key, key)
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This key is invalid or unavailable.",
            )

        activated = await self.db.execute(
            update(CourseKeyRequest)
            .where(
                CourseKeyRequest.id == request.id,
                CourseKeyRequest.student_id == student.id,
                CourseKeyRequest.status == CourseKeyRequestStatus.APPROVED,
                CourseKeyRequest.access_key == key,
                CourseKeyRequest.activated_at.is_(None),
            )
            .values(
                status=CourseKeyRequestStatus.ACTIVATED,
                activated_at=datetime.now(timezone.utc),
                access_key=None,
            )
        )
        if activated.rowcount != 1:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This key has already been activated.",
            )

        unlock = CourseUnlock(
            student_id=student.id,
            course_id=request.course_id,
            request_id=request.id,
        )
        self.db.add(unlock)
        enrollment = await self.db.scalar(
            select(Enrollment).where(
                Enrollment.student_id == student.id,
                Enrollment.course_id == request.course_id,
            )
        )
        if enrollment is None:
            self.db.add(
                Enrollment(
                    student_id=student.id,
                    course_id=request.course_id,
                    status=EnrollmentStatus.ACTIVE,
                )
            )
        elif enrollment.status != EnrollmentStatus.ACTIVE:
            enrollment.status = EnrollmentStatus.ACTIVE

        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This course has already been unlocked.",
            ) from exc
        await self.db.refresh(unlock)
        return unlock

    @staticmethod
    def _generate_unique_key() -> str:
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        return "SB-" + "-".join(
            "".join(secrets.choice(alphabet) for _ in range(5))
            for _ in range(2)
        )
