import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.core.logging import logger
from app.db.models.course import Course, Enrollment, EnrollmentStatus
from app.db.models.user import User, UserRole, UserStatus
from app.db.session import get_db
from app.schemas.course import (
    AdminCourseCreate,
    AdminCourseResponse,
    AdminCourseUpdate,
    AdminStudentResponse,
    AdminCourseTeacherUpdate,
    AdminTeacherResponse,
)
from app.services.course_service import CourseService

router = APIRouter(
    prefix="/courses",
    tags=["Admin Courses"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)


def _course_response(course: Course, enrolled_students: int | None = None) -> AdminCourseResponse:
    return AdminCourseResponse.model_validate(course).model_copy(
        update={
            "enrolled_students": (
                enrolled_students
                if enrolled_students is not None
                else sum(
                    enrollment.status == EnrollmentStatus.ACTIVE
                    for enrollment in course.enrollments
                )
            ),
            "teacher_ids": [
                assignment.teacher_id for assignment in course.teacher_assignments
            ]
            or [course.teacher_id],
            "student_ids": [
                enrollment.student_id
                for enrollment in course.enrollments
                if enrollment.status == EnrollmentStatus.ACTIVE
            ],
        }
    )


@router.get("", response_model=List[AdminCourseResponse])
async def list_admin_courses(db: AsyncSession = Depends(get_db)):
    courses = await CourseService(db).list_admin_courses()
    return [_course_response(course, enrolled_count) for course, enrolled_count in courses]


@router.get("/teachers", response_model=List[AdminTeacherResponse])
async def list_course_teachers(db: AsyncSession = Depends(get_db)):
    teachers = await db.scalars(
        select(User)
        .where(User.role == UserRole.TEACHER, User.status == UserStatus.ACTIVE)
        .order_by(User.full_name)
    )
    return teachers.all()


@router.get("/students", response_model=List[AdminStudentResponse])
async def list_course_students(db: AsyncSession = Depends(get_db)):
    students = await db.scalars(
        select(User)
        .where(User.role == UserRole.STUDENT)
        .order_by(User.full_name)
    )
    return [
        {
            "id": student.id,
            "full_name": student.full_name,
            "email": student.email,
            "is_active": student.status == UserStatus.ACTIVE,
        }
        for student in students.all()
    ]


@router.patch("/{course_id}/teacher", response_model=AdminCourseResponse)
async def assign_course_teacher(
    course_id: uuid.UUID,
    data: AdminCourseTeacherUpdate,
    db: AsyncSession = Depends(get_db),
):
    course = await CourseService(db).assign_course_teacher(
        course_id, data.teacher_id
    )
    enrolled_count = await db.scalar(
        select(func.count(Enrollment.id))
        .where(
            Enrollment.course_id == course.id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
    )
    return _course_response(course, int(enrolled_count or 0))


@router.post("", response_model=AdminCourseResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_course(
    data: AdminCourseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        course, enrolled_count = await CourseService(db).create_admin_course(
            data, current_user
        )
    except IntegrityError as exc:
        logger.warning("Admin course creation failed due to database constraint: %s", exc.orig)
        existing_course = await db.scalar(
            select(Course.id).where(Course.code == data.code.strip().upper())
        )
        if existing_course:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A course with this code already exists.",
            ) from exc
        raise

    return _course_response(course, enrolled_count)


@router.patch("/{course_id}", response_model=AdminCourseResponse)
async def update_admin_course(
    course_id: uuid.UUID,
    data: AdminCourseUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        course, enrolled_count = await CourseService(db).update_admin_course(
            course_id, data
        )
    except IntegrityError as exc:
        logger.warning("Admin course update failed due to database constraint: %s", exc.orig)
        existing_course = await db.scalar(
            select(Course.id).where(
                Course.code == (data.code or "").strip().upper(),
                Course.id != course_id,
            )
        )
        if data.code and existing_course:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A course with this code already exists.",
            ) from exc
        raise
    return _course_response(course, enrolled_count)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_course(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await CourseService(db).delete_admin_course(course_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
