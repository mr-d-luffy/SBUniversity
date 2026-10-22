import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.db.models.user import Department, User, UserRole, UserStatus
from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.common import PaginatedResponse
from app.schemas.course import EnrollmentCreate, EnrollmentResponse
from app.schemas.user import (
    AdminUserAcademicUpdate,
    DepartmentCreate,
    DepartmentResponse,
    RoleUpdateRequest,
    StatusUpdateRequest,
    UserResponse,
    UserStatsResponse,
)
from app.services.course_service import CourseService
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Admin Users"], dependencies=[Depends(require_role(UserRole.ADMIN))])


@router.get("/stats", response_model=UserStatsResponse)
async def get_users_stats_admin(
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    return await repo.get_user_stats()


@router.get("/departments", response_model=List[DepartmentResponse])
async def list_user_departments_admin(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department).order_by(Department.name))
    return list(result.scalars().all())


@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_user_department_admin(
    body: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
):
    name = body.name.strip()
    code = body.code.strip().upper()
    existing = await db.scalar(
        select(Department).where(
            or_(
                func.lower(Department.name) == name.lower(),
                func.lower(Department.code) == code.lower(),
            )
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department name or code is already in use",
        )

    department = Department(name=name, code=code)
    db.add(department)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department name or code is already in use",
        ) from exc
    await db.refresh(department)
    return department


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users_admin(
    role: Optional[UserRole] = None,
    status: Optional[UserStatus] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    users, total = await repo.list_users(role=role, status=status, search=search, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: uuid.UUID,
    body: RoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    user = await service.change_role(user_id, body.role, current_user)
    return user


@router.patch("/{user_id}/academic-details", response_model=UserResponse)
async def update_user_academic_details(
    user_id: uuid.UUID,
    body: AdminUserAcademicUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await UserService(db).update_academic_details(user_id, body, current_user)
    return user


@router.patch("/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: uuid.UUID,
    body: StatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    user = await service.change_status(user_id, body.status, current_user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await UserService(db).delete_account(user_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/enrollments", response_model=EnrollmentResponse)
async def enroll_student_admin(
    body: EnrollmentCreate,
    db: AsyncSession = Depends(get_db),
):
    service = CourseService(db)
    enrollment = await service.enroll_student(body.student_id, body.course_id)
    return enrollment
