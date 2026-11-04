import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user, require_role
from app.db.models.course import Enrollment, EnrollmentStatus
from app.db.models.notice import NoticeAudience
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.repositories.course_repository import CourseRepository
from app.repositories.notice_repository import NoticeRepository
from app.services.course_access_service import unlocked_course_ids
from app.schemas.notice import NoticeCreate, NoticeResponse, NoticeUpdate
from app.services.notice_service import NoticeService

router = APIRouter(prefix="/notices", tags=["Notices"])


@router.get("", response_model=List[NoticeResponse])
async def list_notices(
    audience: Optional[NoticeAudience] = None,
    course_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = NoticeRepository(db)
    course_repo = CourseRepository(db)

    enrolled_ids = []
    if current_user.role == UserRole.STUDENT:
        enrollments = await course_repo.list_student_enrollments(current_user.id)
        unlocked_ids = await unlocked_course_ids(db, current_user.id)
        enrolled_ids = [
            e.course_id
            for e in enrollments
            if e.status == EnrollmentStatus.ACTIVE and e.course_id in unlocked_ids
        ]

    notices, _ = await repo.list_notices(
        audience=audience,
        course_id=course_id,
        enrolled_course_ids=enrolled_ids,
        is_teacher=(current_user.role == UserRole.TEACHER),
        is_admin=(current_user.role == UserRole.ADMIN),
    )

    res = []
    for n in notices:
        nr = NoticeResponse.model_validate(n)
        nr.author_name = n.author.full_name if n.author else "Admin"
        nr.course_title = n.course.title if n.course else None
        res.append(nr)
    return res


@router.post("", response_model=NoticeResponse)
async def create_notice(
    data: NoticeCreate,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    service = NoticeService(db)
    notice = await service.create_notice(data, current_user)
    nr = NoticeResponse.model_validate(notice)
    nr.author_name = current_user.full_name
    return nr


@router.patch("/{notice_id}", response_model=NoticeResponse)
async def update_notice(
    notice_id: uuid.UUID,
    data: NoticeUpdate,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    service = NoticeService(db)
    notice = await service.update_notice(notice_id, data, current_user)
    return notice


@router.delete("/{notice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notice(
    notice_id: uuid.UUID,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    service = NoticeService(db)
    await service.delete_notice(notice_id, current_user)
    return None
