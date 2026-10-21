import uuid
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models.audit import AuditLog
from app.db.models.course import Course, CourseTeacher, Enrollment, EnrollmentStatus
from app.db.models.exam import Exam
from app.db.models.task import Task
from app.db.models.user import User, UserRole, UserStatus
from app.repositories.course_repository import CourseRepository
from app.repositories.user_repository import UserRepository
from app.schemas.course import AdminCourseCreate, AdminCourseUpdate, CourseCreate, CourseUpdate


class CourseService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.course_repo = CourseRepository(db)
        self.user_repo = UserRepository(db)

    async def create_course(self, data: CourseCreate, creator: User) -> Course:
        teacher_id = data.teacher_id or creator.id
        if creator.role == UserRole.TEACHER:
            teacher_id = creator.id

        course = Course(
            code=data.code,
            title=data.title,
            description=data.description,
            department_id=data.department_id,
            teacher_id=teacher_id,
            is_published=data.is_published,
        )
        return await self.course_repo.create(course)

    async def create_admin_course(
        self,
        data: AdminCourseCreate,
        creator: User,
    ) -> tuple[Course, int]:
        selected_teacher_ids = list(dict.fromkeys(data.teacher_ids))
        if not selected_teacher_ids and data.teacher_id:
            selected_teacher_ids = [data.teacher_id]
        if not selected_teacher_ids:
            default_teacher_id = await self.db.scalar(
                select(User.id)
                .where(
                    User.role == UserRole.TEACHER,
                    User.status == UserStatus.ACTIVE,
                )
                .order_by(User.full_name)
                .limit(1)
            )
            if default_teacher_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Create or activate a teacher account before creating a course.",
                )
            selected_teacher_ids = [default_teacher_id]
        if selected_teacher_ids:
            selected_teacher_ids = await self._validate_teacher_ids(selected_teacher_ids)

        course = Course(
            code=data.code.strip().upper(),
            title=data.title.strip(),
            description=data.description,
            department_id=data.department_id,
            teacher_id=selected_teacher_ids[0] if selected_teacher_ids else creator.id,
            is_published=data.is_published,
        )
        try:
            self.db.add(course)
            await self.db.flush()
            self.db.add_all(
                CourseTeacher(course_id=course.id, teacher_id=teacher_id)
                for teacher_id in selected_teacher_ids
            )

            student_ids = set(data.student_ids)
            if data.enroll_all_active_students:
                student_ids.update(await self._list_active_student_ids())
            valid_student_ids = await self._validate_student_ids(student_ids)
            self.db.add_all(
                Enrollment(
                    student_id=student_id,
                    course_id=course.id,
                    status=EnrollmentStatus.ACTIVE,
                )
                for student_id in valid_student_ids
            )

            await self.db.commit()
            course = await self.db.scalar(
                select(Course)
                .options(
                    selectinload(Course.teacher_assignments),
                    selectinload(Course.enrollments),
                )
                .where(Course.id == course.id)
            )
            return course, len(valid_student_ids)
        except Exception:
            await self.db.rollback()
            raise

    async def list_admin_courses(self) -> list[tuple[Course, int]]:
        stmt = (
            select(Course, func.count(Enrollment.id))
            .options(
                selectinload(Course.teacher_assignments),
                selectinload(Course.enrollments),
            )
            .outerjoin(
                Enrollment,
                (Enrollment.course_id == Course.id)
                & (Enrollment.status == EnrollmentStatus.ACTIVE),
            )
            .group_by(Course.id)
            .order_by(Course.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return [(course, int(count)) for course, count in result.all()]

    async def update_admin_course(
        self, course_id: uuid.UUID, data: AdminCourseUpdate
    ) -> tuple[Course, int]:
        course = await self.db.scalar(
            select(Course)
            .options(
                selectinload(Course.teacher_assignments),
                selectinload(Course.enrollments),
            )
            .where(Course.id == course_id)
        )
        if course is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
            )

        fields = data.model_dump(exclude_unset=True)
        teacher_ids = fields.pop("teacher_ids", None)
        student_ids = fields.pop("student_ids", None)
        enroll_all = fields.pop("enroll_all_active_students", None)
        for field, value in fields.items():
            if field in {"code", "title"} and value is None:
                continue
            if field == "code" and value is not None:
                value = value.strip().upper()
            elif field == "title" and value is not None:
                value = value.strip()
            elif field == "description" and value is not None:
                value = value.strip() or None
            setattr(course, field, value)

        if teacher_ids is not None:
            unique_teacher_ids = list(dict.fromkeys(teacher_ids))
            if not unique_teacher_ids:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Assign at least one active teacher to the course.",
                )
            valid_teacher_ids = await self._validate_teacher_ids(unique_teacher_ids)
            course.teacher_id = valid_teacher_ids[0]
            course.teacher_assignments.clear()
            course.teacher_assignments.extend(
                CourseTeacher(teacher_id=teacher_id)
                for teacher_id in valid_teacher_ids
            )

        requested_student_ids = set(student_ids or [])
        if enroll_all:
            requested_student_ids.update(await self._list_active_student_ids())
        if student_ids is not None or enroll_all:
            existing = {
                enrollment.student_id: enrollment
                for enrollment in course.enrollments
            }
            retained_existing_ids = {
                student_id
                for student_id, enrollment in existing.items()
                if enrollment.status == EnrollmentStatus.ACTIVE
            }
            valid_student_ids = await self._validate_student_ids(
                requested_student_ids,
                allowed_existing_ids=retained_existing_ids,
            )
            selected_student_ids = set(valid_student_ids)
            for student_id, enrollment in existing.items():
                if (
                    enrollment.status == EnrollmentStatus.ACTIVE
                    and student_id not in selected_student_ids
                ):
                    # Keep the enrollment record (and its progress) while removing
                    # the student's active access to this course.
                    enrollment.status = EnrollmentStatus.DROPPED

            for student_id in selected_student_ids:
                enrollment = existing.get(student_id)
                if enrollment is None:
                    course.enrollments.append(
                        Enrollment(
                            student_id=student_id,
                            status=EnrollmentStatus.ACTIVE,
                        )
                    )
                elif enrollment.status == EnrollmentStatus.DROPPED:
                    enrollment.status = EnrollmentStatus.ACTIVE

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        course = await self.db.scalar(
            select(Course)
            .options(
                selectinload(Course.teacher_assignments),
                selectinload(Course.enrollments),
            )
            .where(Course.id == course_id)
        )
        active_count = sum(
            enrollment.status == EnrollmentStatus.ACTIVE
            for enrollment in course.enrollments
        )
        return course, active_count

    async def delete_admin_course(
        self, course_id: uuid.UUID, admin: User
    ) -> None:
        course = await self.course_repo.get_by_id(course_id)
        if course is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
            )

        tasks = (
            await self.db.scalars(select(Task).where(Task.course_id == course_id))
        ).all()
        for task in tasks:
            await self.db.delete(task)
        await self.db.flush()

        exams = (
            await self.db.scalars(select(Exam).where(Exam.course_id == course_id))
        ).all()
        for exam in exams:
            await self.db.delete(exam)
        await self.db.flush()

        self.db.add(
            AuditLog(
                actor_id=admin.id,
                action="course.deleted",
                entity_type="course",
                entity_id=str(course_id),
                metadata_={"code": course.code, "title": course.title},
            )
        )
        await self.db.delete(course)
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

    async def assign_course_teacher(
        self, course_id: uuid.UUID, teacher_id: uuid.UUID
    ) -> Course:
        course = await self.course_repo.get_by_id(course_id)
        if course is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
            )
        course.teacher_id = await self._validate_teacher_id(teacher_id)
        course.teacher_assignments.clear()
        course.teacher_assignments.append(CourseTeacher(teacher_id=teacher_id))
        return await self.course_repo.update(course)

    async def _validate_teacher_id(self, teacher_id: uuid.UUID) -> uuid.UUID:
        teacher = await self.db.scalar(
            select(User.id).where(
                User.id == teacher_id,
                User.role == UserRole.TEACHER,
                User.status == UserStatus.ACTIVE,
            )
        )
        if teacher is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Choose an active teacher account.",
            )
        return teacher

    async def _validate_teacher_ids(
        self, teacher_ids: list[uuid.UUID]
    ) -> list[uuid.UUID]:
        teachers = set(
            (
                await self.db.scalars(
                    select(User.id).where(
                        User.id.in_(teacher_ids),
                        User.role == UserRole.TEACHER,
                        User.status == UserStatus.ACTIVE,
                    )
                )
            ).all()
        )
        if teachers != set(teacher_ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Every assigned teacher must be an active teacher account.",
            )
        return teacher_ids

    async def _list_active_student_ids(self) -> set[uuid.UUID]:
        return set(
            (
                await self.db.scalars(
                    select(User.id).where(
                        User.role == UserRole.STUDENT,
                        User.status == UserStatus.ACTIVE,
                    )
                )
            ).all()
        )

    async def _validate_student_ids(
        self,
        student_ids: set[uuid.UUID],
        allowed_existing_ids: set[uuid.UUID] | None = None,
    ) -> set[uuid.UUID]:
        if not student_ids:
            return set()
        active_student_ids = set(
            (
                await self.db.scalars(
                    select(User.id).where(
                        User.id.in_(student_ids),
                        User.role == UserRole.STUDENT,
                        User.status == UserStatus.ACTIVE,
                    )
                )
            ).all()
        )
        allowed_existing_ids = allowed_existing_ids or set()
        if not student_ids.issubset(active_student_ids | allowed_existing_ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Every selected student must be an active student account.",
            )
        return student_ids

    async def update_course(self, course_id: uuid.UUID, data: CourseUpdate, user: User) -> Course:
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

        if user.role == UserRole.TEACHER and not await self.course_repo.is_teacher_assigned(
            course.id, user.id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        for field, val in data.model_dump(exclude_unset=True).items():
            setattr(course, field, val)

        return await self.course_repo.update(course)

    async def enroll_student(self, student_id: uuid.UUID, course_id: uuid.UUID) -> Enrollment:
        existing = await self.course_repo.get_enrollment(student_id, course_id)
        if existing:
            return existing

        enrollment = Enrollment(student_id=student_id, course_id=course_id, status=EnrollmentStatus.ACTIVE)
        return await self.course_repo.create_enrollment(enrollment)
