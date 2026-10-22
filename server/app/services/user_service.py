import uuid
from typing import Optional
from fastapi import HTTPException, status
import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.logging import logger
from app.db.models.audit import AuditLog
from app.db.models.course import Course, CourseTeacher
from app.db.models.user import StudentProfile, TeacherProfile, User, UserRole, UserStatus
from app.repositories.audit_repository import AuditRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserUpdate, VirtualIDCardResponse
from app.services.ranking_service import RankingService


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditRepository(db)
        self.ranking_service = RankingService(db)

    async def get_virtual_id_card(self, user: User) -> VirtualIDCardResponse:
        profile = user.student_profile
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")

        dept_name = profile.department.name if profile.department else "General Studies"
        verify_url = f"{settings.FRONTEND_ORIGIN}/verify/student/{profile.qr_token}"

        return VirtualIDCardResponse(
            name=user.full_name,
            student_code=profile.student_code,
            department=dept_name,
            batch_year=profile.batch_year,
            phone=profile.phone,
            photo_url=profile.photo_path or user.avatar_url,
            valid_until=profile.id_valid_until,
            qr_verify_url=verify_url,
            status=user.status.value,
        )

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        if data.full_name is not None:
            user.full_name = data.full_name
        if data.avatar_url is not None:
            user.avatar_url = data.avatar_url

        if user.student_profile and data.phone is not None:
            user.student_profile.phone = data.phone
        if user.student_profile and data.date_of_birth is not None:
            user.student_profile.date_of_birth = data.date_of_birth

        return await self.user_repo.update(user)

    async def change_role(self, user_id: uuid.UUID, new_role: UserRole, admin: User) -> User:
        if admin.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can change user roles")

        target_user = await self.user_repo.get_by_id(user_id)
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if target_user.role == UserRole.TEACHER and new_role != UserRole.TEACHER:
            assigned_course = await self.db.scalar(
                select(Course.id)
                .where(
                    or_(
                        Course.teacher_id == target_user.id,
                        Course.teacher_assignments.any(
                            CourseTeacher.teacher_id == target_user.id
                        ),
                    )
                )
                .limit(1)
            )
            if assigned_course is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Reassign this teacher's courses before changing their role.",
                )

        old_role = target_user.role
        # Sync with Clerk Backend API
        if settings.CLERK_SECRET_KEY and target_user.clerk_user_id:
            try:
                url = f"https://api.clerk.com/v1/users/{target_user.clerk_user_id}/metadata"
                headers = {"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"}
                payload = {"public_metadata": {"role": new_role.value}}
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.patch(url, headers=headers, json=payload)
                    if not 200 <= resp.status_code < 300:
                        logger.error("Clerk role sync failed with status %d", resp.status_code)
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail="Role update could not be synchronized. Please try again.",
                        )
            except httpx.RequestError as e:
                logger.error("Failed to sync role with Clerk API: %s", e)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Role update could not be synchronized. Please try again.",
                ) from e

        target_user.role = new_role
        # Audit log
        await self.audit_repo.log(
            actor_id=admin.id,
            action="user.role_changed",
            entity_type="user",
            entity_id=str(target_user.id),
            metadata={"old_role": old_role.value, "new_role": new_role.value},
        )

        return await self.user_repo.update(target_user)

    async def change_status(self, user_id: uuid.UUID, new_status: UserStatus, admin: User) -> User:
        if admin.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can change user status")

        target_user = await self.user_repo.get_by_id(user_id)
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        old_status = target_user.status
        target_user.status = new_status

        await self.audit_repo.log(
            actor_id=admin.id,
            action="user.status_changed",
            entity_type="user",
            entity_id=str(target_user.id),
            metadata={"old_status": old_status.value, "new_status": new_status.value},
        )

        updated_user = await self.user_repo.update(target_user)

        # Refresh ranking (removes from leaderboard if suspended/deleted, or restores if active)
        await self.ranking_service.refresh_student(target_user.id)
        return updated_user

    async def delete_account(self, user_id: uuid.UUID, admin: User) -> None:
        if admin.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can delete user accounts.",
            )
        if user_id == admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot delete your own administrator account.",
            )

        target_user = await self.user_repo.get_by_id(user_id)
        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )
        if target_user.role == UserRole.ADMIN and target_user.status == UserStatus.ACTIVE:
            active_admins = await self.db.scalar(
                select(func.count(User.id)).where(
                    User.role == UserRole.ADMIN,
                    User.status == UserStatus.ACTIVE,
                )
            )
            if int(active_admins or 0) <= 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The last active administrator account cannot be deleted.",
                )

        assigned_course = await self.db.scalar(
            select(Course.id).where(
                or_(
                    Course.teacher_id == target_user.id,
                    Course.teacher_assignments.any(
                        CourseTeacher.teacher_id == target_user.id
                    ),
                )
            ).limit(1)
        ) if target_user.role == UserRole.TEACHER else None
        if assigned_course is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Reassign this teacher's courses before deleting the account.",
            )

        if not settings.CLERK_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Account deletion is unavailable because identity-provider deletion is not configured.",
            )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.delete(
                    f"https://api.clerk.com/v1/users/{target_user.clerk_user_id}",
                    headers={
                        "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"
                    },
                )
        except httpx.RequestError as exc:
            logger.error("Identity-provider account deletion request failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not delete the account from the identity provider. No database records were removed.",
            ) from exc

        if response.status_code not in {200, 204, 404}:
            logger.error(
                "Identity-provider account deletion failed with status %d",
                response.status_code,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The identity provider did not delete the account. No database records were removed.",
            )

        self.db.add(
            AuditLog(
                actor_id=admin.id,
                action="user.deleted",
                entity_type="user",
                entity_id=str(target_user.id),
                metadata_={
                    "email": target_user.email,
                    "full_name": target_user.full_name,
                    "role": target_user.role.value,
                },
            )
        )
        await self.db.delete(target_user)
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            logger.exception("Database account deletion failed for user %s", user_id)
            raise
