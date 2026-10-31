from app.db.base import Base
from app.db.models.user import (
    User,
    UserRole,
    UserStatus,
    UserVerificationStatus,
    Department,
    StudentProfile,
    TeacherProfile,
)
from app.db.models.course import Course, CourseTeacher, Enrollment, EnrollmentStatus
from app.db.models.exam import Exam, ExamStatus, Question, QuestionOption, ExamAttempt, AttemptStatus, AttemptAnswer
from app.db.models.result import Result
from app.db.models.certificate import Certificate
from app.db.models.task import (
    Task,
    TaskType,
    TaskVerification,
    TaskStatus,
    TaskResourceType,
    TaskAssignmentScope,
    TaskRecipient,
    TaskCompletion,
    TaskVideoProgress,
    CompletionStatus,
)
from app.db.models.notice import Notice, NoticeAudience, NoticePriority, NoticeStatus
from app.db.models.chat import (
    ChatSession,
    ChatMessage,
    ChatRole,
    CommunityConversation,
    CommunityConversationKind,
    CommunityMessage,
    CommunityChatDevice,
    CommunityConversationKeyEnvelope,
)
from app.db.models.planner import PlannerEntry, PlannerEntryKind, PlannerNoteShape
from app.db.models.whiteboard import (
    WhiteboardMessage,
    WhiteboardSession,
    WhiteboardStroke,
)
from app.db.models.audit import AuditLog
from app.db.models.activity import UserActivityDay
from app.db.models.security_event import SecurityRequestEvent

__all__ = [
    "Base",
    "User",
    "UserRole",
    "UserStatus",
    "UserVerificationStatus",
    "Department",
    "StudentProfile",
    "TeacherProfile",
    "Course",
    "CourseTeacher",
    "Enrollment",
    "EnrollmentStatus",
    "Exam",
    "ExamStatus",
    "Question",
    "QuestionOption",
    "ExamAttempt",
    "AttemptStatus",
    "AttemptAnswer",
    "Result",
    "Certificate",
    "Task",
    "TaskType",
    "TaskVerification",
    "TaskStatus",
    "TaskResourceType",
    "TaskAssignmentScope",
    "TaskRecipient",
    "TaskCompletion",
    "TaskVideoProgress",
    "CompletionStatus",
    "Notice",
    "NoticeAudience",
    "NoticePriority",
    "NoticeStatus",
    "ChatSession",
    "ChatMessage",
    "ChatRole",
    "CommunityConversation",
    "CommunityConversationKind",
    "CommunityMessage",
    "CommunityChatDevice",
    "CommunityConversationKeyEnvelope",
    "PlannerEntry",
    "PlannerEntryKind",
    "PlannerNoteShape",
    "WhiteboardSession",
    "WhiteboardStroke",
    "WhiteboardMessage",
    "AuditLog",
    "UserActivityDay",
    "SecurityRequestEvent",
]
