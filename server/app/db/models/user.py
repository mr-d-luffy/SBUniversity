import enum
import uuid
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM as PostgreSQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class UserVerificationStatus(str, enum.Enum):
    NOT_VERIFIED = "not_verified"
    VERIFIED = "verified"


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    clerk_user_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda obj: [e.value for e in obj]),
        default=UserRole.STUDENT,
        nullable=False,
        index=True,
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status", values_callable=lambda obj: [e.value for e in obj]),
        default=UserStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    student_profile: Mapped[Optional["StudentProfile"]] = relationship("StudentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    teacher_profile: Mapped[Optional["TeacherProfile"]] = relationship("TeacherProfile", back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    courses_taught: Mapped[List["Course"]] = relationship("Course", back_populates="teacher", foreign_keys="Course.teacher_id", passive_deletes="all")
    course_assignments: Mapped[List["CourseTeacher"]] = relationship(
        "CourseTeacher", back_populates="teacher", passive_deletes=True
    )
    enrollments: Mapped[List["Enrollment"]] = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    exam_attempts: Mapped[List["ExamAttempt"]] = relationship("ExamAttempt", back_populates="student", cascade="all, delete-orphan")
    results: Mapped[List["Result"]] = relationship("Result", back_populates="student", cascade="all, delete-orphan")
    certificates: Mapped[List["Certificate"]] = relationship("Certificate", back_populates="student", foreign_keys="Certificate.student_id", cascade="all, delete-orphan")
    task_completions: Mapped[List["TaskCompletion"]] = relationship("TaskCompletion", back_populates="student", foreign_keys="TaskCompletion.student_id", cascade="all, delete-orphan")
    notices_authored: Mapped[List["Notice"]] = relationship("Notice", back_populates="author")
    chat_sessions: Mapped[List["ChatSession"]] = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")


class Department(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "departments"

    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    courses: Mapped[List["Course"]] = relationship("Course", back_populates="department")
    students: Mapped[List["StudentProfile"]] = relationship("StudentProfile", back_populates="department")
    teachers: Mapped[List["TeacherProfile"]] = relationship("TeacherProfile", back_populates="department")


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    student_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    batch_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    academic_term: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    verification_status: Mapped[UserVerificationStatus] = mapped_column(
        PostgreSQLEnum(
            UserVerificationStatus,
            name="user_verification_status",
            values_callable=lambda values: [value.value for value in values],
        ),
        default=UserVerificationStatus.NOT_VERIFIED,
        server_default=UserVerificationStatus.NOT_VERIFIED.value,
        nullable=False,
    )
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    photo_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    id_valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    qr_token: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="student_profile")
    department: Mapped[Optional["Department"]] = relationship("Department", back_populates="students", lazy="selectin")


class TeacherProfile(Base):
    __tablename__ = "teacher_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    employee_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    verification_status: Mapped[UserVerificationStatus] = mapped_column(
        PostgreSQLEnum(
            UserVerificationStatus,
            name="user_verification_status",
            values_callable=lambda values: [value.value for value in values],
            create_type=False,
        ),
        default=UserVerificationStatus.NOT_VERIFIED,
        server_default=UserVerificationStatus.NOT_VERIFIED.value,
        nullable=False,
    )
    designation: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="teacher_profile")
    department: Mapped[Optional["Department"]] = relationship("Department", back_populates="teachers", lazy="selectin")
