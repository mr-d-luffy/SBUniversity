import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator
from app.db.models.task import (
    CompletionStatus,
    TaskAssignmentScope,
    TaskResourceType,
    TaskStatus,
    TaskType,
    TaskVerification,
)


class TaskCreate(BaseModel):
    course_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    points: int = Field(ge=0)
    due_at: Optional[datetime] = None
    resource_type: Optional[TaskResourceType] = None
    resource_url: Optional[AnyHttpUrl] = None
    assignment_scope: TaskAssignmentScope = TaskAssignmentScope.ALL_STUDENTS
    target_student_ids: List[uuid.UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_resource_and_recipients(self):
        if (self.resource_type is None) != (self.resource_url is None):
            raise ValueError("resource_type and resource_url must be provided together")
        if self.assignment_scope == TaskAssignmentScope.SELECTED_STUDENTS and not self.target_student_ids:
            raise ValueError("Select at least one student for an individually assigned task")
        if self.assignment_scope == TaskAssignmentScope.ALL_STUDENTS and self.target_student_ids:
            raise ValueError("target_student_ids must be empty when assigning to all students")
        return self


class TaskUpdate(BaseModel):
    course_id: Optional[uuid.UUID] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=10000)
    points: Optional[int] = Field(default=None, ge=0)
    due_at: Optional[datetime] = None
    resource_type: Optional[TaskResourceType] = None
    resource_url: Optional[AnyHttpUrl] = None
    assignment_scope: Optional[TaskAssignmentScope] = None
    target_student_ids: Optional[List[uuid.UUID]] = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    course_id: uuid.UUID
    course_title: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    type: TaskType
    exam_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    points: int
    verification: TaskVerification
    due_at: Optional[datetime] = None
    resource_type: Optional[TaskResourceType] = None
    resource_url: Optional[str] = None
    assignment_scope: TaskAssignmentScope = TaskAssignmentScope.ALL_STUDENTS
    target_student_ids: Optional[List[uuid.UUID]] = None
    status: TaskStatus
    created_at: datetime
    # Student view augmentation
    my_completion_id: Optional[uuid.UUID] = None
    my_status: Optional[CompletionStatus] = None
    points_earned: Optional[int] = None
    my_video_progress: Optional[float] = None


class TaskVideoProgressRequest(BaseModel):
    progress_percent: float = Field(ge=0, le=100)
    video_duration_seconds: float = Field(gt=0, le=43200)


class TaskVideoProgressResponse(BaseModel):
    progress_percent: float


class TaskCompleteRequest(BaseModel):
    note: Optional[str] = None
    url: Optional[str] = None


class TaskCompletionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    task_id: uuid.UUID
    task_title: Optional[str] = None
    course_id: Optional[uuid.UUID] = None
    course_title: Optional[str] = None
    student_id: uuid.UUID
    student_name: Optional[str] = None
    status: CompletionStatus
    submission_note: Optional[str] = None
    submission_url: Optional[str] = None
    points_awarded: int
    points_available: Optional[int] = None
    submitted_at: datetime
    completed_at: Optional[datetime] = None
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None


class TaskReviewRequest(BaseModel):
    review_note: Optional[str] = None


class TaskPointsHistoryItem(BaseModel):
    completion_id: uuid.UUID
    task_id: uuid.UUID
    task_title: str
    course_title: str
    points: int
    completed_at: datetime


class StudentPointsResponse(BaseModel):
    total_points: int
    tasks_completed: int
    rank: Optional[int] = None
    history: List[TaskPointsHistoryItem] = []


class TeacherTaskStudentOption(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str


class TeacherTaskCourseOption(BaseModel):
    id: uuid.UUID
    title: str
    code: str
