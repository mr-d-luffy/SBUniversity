import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EnrollmentStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DROPPED = "dropped"


class CourseKeyRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVATED = "activated"


class Course(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_courses_price_nonnegative"),
        CheckConstraint(
            "discount_percent >= 0 AND discount_percent <= 100",
            name="ck_courses_discount_percent",
        ),
    )

    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    teacher_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    discount_percent: Mapped[int] = mapped_column(default=0, nullable=False)

    department: Mapped[Optional["Department"]] = relationship("Department", back_populates="courses")
    teacher: Mapped["User"] = relationship("User", back_populates="courses_taught", foreign_keys=[teacher_id])
    teacher_assignments: Mapped[List["CourseTeacher"]] = relationship(
        "CourseTeacher",
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    enrollments: Mapped[List["Enrollment"]] = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    exams: Mapped[List["Exam"]] = relationship("Exam", back_populates="course", cascade="all, delete-orphan")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="course", cascade="all, delete-orphan")
    certificates: Mapped[List["Certificate"]] = relationship("Certificate", back_populates="course", cascade="all, delete-orphan")
    notices: Mapped[List["Notice"]] = relationship("Notice", back_populates="course", cascade="all, delete-orphan")


class CourseTeacher(Base):
    __tablename__ = "course_teachers"
    __table_args__ = (
        Index("ix_course_teachers_teacher_id", "teacher_id"),
    )

    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    course: Mapped["Course"] = relationship("Course", back_populates="teacher_assignments")
    teacher: Mapped["User"] = relationship("User", back_populates="course_assignments")


class Enrollment(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_enrollment_student_course"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(EnrollmentStatus, name="enrollment_status", values_callable=lambda obj: [e.value for e in obj]),
        default=EnrollmentStatus.ACTIVE,
        nullable=False,
    )
    progress_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0.00, nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    student: Mapped["User"] = relationship("User", back_populates="enrollments")
    course: Mapped["Course"] = relationship("Course", back_populates="enrollments")


class CourseUnlock(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "course_unlocks"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_course_unlock_student_course"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("course_key_requests.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CourseKeyRequest(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "course_key_requests"
    __table_args__ = (
        Index("ix_course_key_requests_student_status", "student_id", "status"),
        Index(
            "uq_course_key_requests_pending_student_course",
            "student_id",
            "course_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
            sqlite_where=text("status = 'pending'"),
        ),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[CourseKeyRequestStatus] = mapped_column(
        Enum(
            CourseKeyRequestStatus,
            name="course_key_request_status",
            values_callable=lambda obj: [item.value for item in obj],
        ),
        default=CourseKeyRequestStatus.PENDING,
        nullable=False,
    )
    access_key: Mapped[Optional[str]] = mapped_column(String(16), unique=True, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
