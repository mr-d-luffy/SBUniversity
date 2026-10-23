import enum
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ExamStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class AttemptStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    AUTO_SUBMITTED = "auto_submitted"


class Exam(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "exams"
    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="ck_exam_duration"),
        CheckConstraint("end_at > start_at", name="ck_exam_window"),
        CheckConstraint("pass_marks >= 0", name="ck_exam_pass_marks"),
    )

    course_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    total_marks: Mapped[float] = mapped_column(Numeric(7, 2), default=0.00, nullable=False)
    pass_marks: Mapped[float] = mapped_column(Numeric(7, 2), default=0.00, nullable=False)
    negative_marking: Mapped[float] = mapped_column(Numeric(4, 2), default=0.00, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_review: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[ExamStatus] = mapped_column(
        Enum(ExamStatus, name="exam_status", values_callable=lambda obj: [e.value for e in obj]),
        default=ExamStatus.DRAFT,
        nullable=False,
        index=True,
    )

    course: Mapped["Course"] = relationship("Course", back_populates="exams")
    creator: Mapped[Optional["User"]] = relationship("User")
    questions: Mapped[List["Question"]] = relationship("Question", back_populates="exam", cascade="all, delete-orphan", order_by="Question.position")
    attempts: Mapped[List["ExamAttempt"]] = relationship("ExamAttempt", back_populates="exam", cascade="all, delete-orphan")
    results: Mapped[List["Result"]] = relationship("Result", back_populates="exam", cascade="all, delete-orphan")
    task: Mapped[Optional["Task"]] = relationship("Task", back_populates="exam", uselist=False)


class Question(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint("exam_id", "position", name="uq_question_exam_position"),
        CheckConstraint("marks > 0", name="ck_question_marks"),
    )

    exam_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    marks: Mapped[float] = mapped_column(Numeric(5, 2), default=1.00, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    exam: Mapped["Exam"] = relationship("Exam", back_populates="questions")
    options: Mapped[List["QuestionOption"]] = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan", order_by="QuestionOption.position")


class QuestionOption(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "question_options"
    __table_args__ = (
        UniqueConstraint("question_id", "position", name="uq_option_question_position"),
    )

    question_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    question: Mapped["Question"] = relationship("Question", back_populates="options")


class ExamAttempt(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "exam_attempts"
    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", "attempt_no", name="uq_exam_student_attempt"),
    )

    exam_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False, index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[AttemptStatus] = mapped_column(
        Enum(AttemptStatus, name="attempt_status", values_callable=lambda obj: [e.value for e in obj]),
        default=AttemptStatus.IN_PROGRESS,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    integrity_violation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    integrity_violation_reason: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    integrity_flagged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reexam_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reexam_approved_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    exam: Mapped["Exam"] = relationship("Exam", back_populates="attempts")
    student: Mapped["User"] = relationship("User", back_populates="exam_attempts", foreign_keys=[student_id])
    answers: Mapped[List["AttemptAnswer"]] = relationship("AttemptAnswer", back_populates="attempt", cascade="all, delete-orphan")
    result: Mapped[Optional["Result"]] = relationship("Result", back_populates="attempt", uselist=False, cascade="all, delete-orphan")


class AttemptAnswer(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "attempt_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question_answer"),
    )

    attempt_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    selected_option_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("question_options.id", ondelete="SET NULL"), nullable=True)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    attempt: Mapped["ExamAttempt"] = relationship("ExamAttempt", back_populates="answers")
    question: Mapped["Question"] = relationship("Question")
    selected_option: Mapped[Optional["QuestionOption"]] = relationship("QuestionOption")
