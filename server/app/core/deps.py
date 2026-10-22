import uuid
from typing import AsyncGenerator, List, Union
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.config import settings
from app.core.logging import logger
from app.core.redis import get_redis_client
from app.core.security import SecurityError, verify_clerk_token
from app.db.models.course import Course, Enrollment, EnrollmentStatus
from app.db.models.user import Department, StudentProfile, TeacherProfile, User, UserRole, UserStatus
from app.db.session import get_db
from app.repositories.user_repository import UserRepository

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials if credentials and credentials.credentials else None

    if not token:
        logger.warning(
            "Authentication denied path=%s client=%s request_id=%s reason=missing_token",
            request.url.path,
            request.client.host if request.client else "unknown",
            getattr(request.state, "request_id", "unknown"),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Authentication required. Bearer token missing.",
                    "details": None,
                }
            },
        )

    user_repo = UserRepository(db)

    try:
        payload = await verify_clerk_token(token)
    except SecurityError as e:
        logger.warning(
            "Authentication denied path=%s client=%s request_id=%s code=%s",
            request.url.path,
            request.client.host if request.client else "unknown",
            getattr(request.state, "request_id", "unknown"),
            e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "details": None,
                }
            },
        )

    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "Token payload missing subject identifier.",
                    "details": None,
                }
            },
        )

    # Attach clerk id to request state for rate limiting or logging
    request.state.user_id = clerk_user_id

    # Load user from DB
    stmt = (
        select(User)
        .options(
            selectinload(User.student_profile).selectinload(StudentProfile.department),
            selectinload(User.teacher_profile).selectinload(TeacherProfile.department),
        )
        .where(User.clerk_user_id == clerk_user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    async def reload_user(u: User) -> User:
        reload_stmt = (
            select(User)
            .options(
                selectinload(User.student_profile).selectinload(StudentProfile.department),
                selectinload(User.teacher_profile).selectinload(TeacherProfile.department),
            )
            .where(User.id == u.id)
        )
        res = await db.execute(reload_stmt)
        return res.scalar_one()

    async def student_profile_exists(user_id: uuid.UUID) -> bool:
        profile_stmt = select(StudentProfile.user_id).where(StudentProfile.user_id == user_id)
        return (await db.execute(profile_stmt)).scalar_one_or_none() is not None

    if not user:
        # Check if we should auto-provision a basic student record or if in dev mode
        email = payload.get("email") or payload.get("email_address") or f"{clerk_user_id}@sbuniversity.edu"
        name = payload.get("name") or payload.get("full_name") or "SiliconBrains University User"
        metadata = (
            payload.get("public_metadata")
            or payload.get("publicMetadata")
            or payload.get("metadata")
            or {}
        )
        role_claim = payload.get("role") or (
            metadata.get("role") if isinstance(metadata, dict) else None
        )

        # If role is not in the JWT token, fetch directly from Clerk Backend API
        if not role_claim and settings.CLERK_SECRET_KEY:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.get(
                        f"https://api.clerk.com/v1/users/{clerk_user_id}",
                        headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
                    )
                    if resp.status_code == 200:
                        cdata = resp.json()
                        role_claim = cdata.get("public_metadata", {}).get("role")
                        addrs = cdata.get("email_addresses", [])
                        if addrs:
                            email = addrs[0].get("email_address", email)
                        fn = cdata.get("first_name") or ""
                        ln = cdata.get("last_name") or ""
                        full_n = f"{fn} {ln}".strip()
                        if full_n:
                            name = full_n
            except Exception:
                pass

        try:
            user_role = UserRole(role_claim) if role_claim else UserRole.STUDENT
        except ValueError:
            user_role = UserRole.STUDENT

        # Check if an existing record has this email (e.g. from seed or earlier login)
        stmt_email = (
            select(User)
            .options(
                selectinload(User.student_profile).selectinload(StudentProfile.department),
                selectinload(User.teacher_profile).selectinload(TeacherProfile.department),
            )
            .where(User.email == email)
        )
        res_email = await db.execute(stmt_email)
        existing_by_email = res_email.scalar_one_or_none()

        if existing_by_email:
            existing_by_email.clerk_user_id = clerk_user_id
            if user_role and existing_by_email.role != user_role:
                existing_by_email.role = user_role
            user = existing_by_email
            await db.commit()
            user = await reload_user(user)
        else:
            user = User(
                clerk_user_id=clerk_user_id,
                email=email,
                full_name=name,
                avatar_url=payload.get("image_url") or payload.get("picture"),
                role=user_role,
                status=UserStatus.ACTIVE,
            )
            db.add(user)
            await db.flush()

        # If user is student and has no student_profile, create it
        if user.role == UserRole.STUDENT and not await student_profile_exists(user.id):
            student_code = await user_repo.next_student_code(2026)

            dept_stmt = select(Department).limit(1)
            dept = (await db.execute(dept_stmt)).scalar_one_or_none()
            dept_id = dept.id if dept else None

            sp = StudentProfile(
                user_id=user.id,
                student_code=student_code,
                department_id=dept_id,
                batch_year=2026,
                qr_token=str(clerk_user_id),
                phone=payload.get("phone") or "+91 98765 43210",
            )
            db.add(sp)

            # Auto-enroll into published courses
            courses_stmt = select(Course).where(Course.is_published == True)
            courses_to_enroll = (await db.execute(courses_stmt)).scalars().all()
            for c in courses_to_enroll:
                enr = Enrollment(
                    student_id=user.id,
                    course_id=c.id,
                    status=EnrollmentStatus.ACTIVE,
                    progress_percent=0.0,
                )
                db.add(enr)

            await db.commit()
            user = await reload_user(user)
    else:
        # The database role is authoritative for existing accounts; JWT metadata
        # may be stale after a privileged role change.
        # If existing student lacks a profile, auto-create it now
        if user.role == UserRole.STUDENT and not await student_profile_exists(user.id):
            student_code = await user_repo.next_student_code(2026)

            dept_stmt = select(Department).limit(1)
            dept = (await db.execute(dept_stmt)).scalar_one_or_none()
            dept_id = dept.id if dept else None

            sp = StudentProfile(
                user_id=user.id,
                student_code=student_code,
                department_id=dept_id,
                batch_year=2026,
                qr_token=str(clerk_user_id),
                phone=payload.get("phone") or "+91 98765 43210",
            )
            db.add(sp)

            courses_stmt = select(Course).where(Course.is_published == True)
            courses_to_enroll = (await db.execute(courses_stmt)).scalars().all()
            for c in courses_to_enroll:
                enr_check = select(Enrollment).where(Enrollment.student_id == user.id, Enrollment.course_id == c.id)
                if not (await db.execute(enr_check)).scalar_one_or_none():
                    db.add(Enrollment(student_id=user.id, course_id=c.id, status=EnrollmentStatus.ACTIVE, progress_percent=0.0))

            await db.commit()
            user = await reload_user(user)

    # Reject suspended or deleted users
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "ACCOUNT_INACTIVE",
                    "message": f"Account is {user.status.value}. Please contact university administration.",
                    "details": None,
                }
            },
        )

    return user


def require_role(allowed_roles: Union[UserRole, List[UserRole]]):
    if isinstance(allowed_roles, UserRole):
        roles = [allowed_roles]
    else:
        roles = allowed_roles

    async def role_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in roles:
            logger.warning(
                "Authorization denied actor_id=%s role=%s required=%s path=%s request_id=%s",
                current_user.id,
                current_user.role.value,
                ",".join(role.value for role in roles),
                request.url.path,
                getattr(request.state, "request_id", "unknown"),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": f"Access denied. Requires one of the following roles: {[r.value for r in roles]}.",
                        "details": None,
                    }
                },
            )
        return current_user

    return role_checker
