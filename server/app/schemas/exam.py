import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.exam import AttemptStatus, ExamStatus


class QuestionOptionCreate(BaseModel):
    text: str
    is_correct: bool = False
    position: int = Field(ge=1)


class QuestionOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    text: str
    position: int
    is_correct: Optional[bool] = None  # None for student during exam


class QuestionCreate(BaseModel):
    text: str
    marks: float = Field(default=1.0, gt=0)
    position: int = Field(ge=1)
    explanation: Optional[str] = None
    options: List[QuestionOptionCreate] = Field(min_length=2)


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    text: str
    marks: float
    position: int
    explanation: Optional[str] = None
    options: List[QuestionOptionResponse]


class ExamCreate(BaseModel):
    course_id: uuid.UUID
    title: str
    instructions: Optional[str] = None
    duration_minutes: int = Field(gt=0)
    pass_marks: float = Field(ge=0)
    negative_marking: float = Field(default=0.0, ge=0)
    max_attempts: int = Field(default=1, gt=0)
    shuffle_questions: bool = True
    show_review: bool = True
    start_at: datetime
    end_at: datetime
    questions: List[QuestionCreate] = Field(default_factory=list)
    publish_immediately: bool = False
    task_points: int = Field(default=0, ge=0)


class ExamUpdate(BaseModel):
    course_id: Optional[uuid.UUID] = None
    title: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: Optional[int] = Field(default=None, gt=0)
    pass_marks: Optional[float] = Field(default=None, ge=0)
    negative_marking: Optional[float] = Field(default=None, ge=0)
    max_attempts: Optional[int] = Field(default=None, gt=0)
    shuffle_questions: Optional[bool] = None
    show_review: Optional[bool] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    questions: Optional[List[QuestionCreate]] = None
    task_points: Optional[int] = Field(default=None, ge=0)


class ExamPublishRequest(BaseModel):
    task_points: int = Field(default=0, ge=0)


class ExamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    course_id: uuid.UUID
    created_by: Optional[uuid.UUID] = None
    title: str
    instructions: Optional[str] = None
    duration_minutes: int
    total_marks: float
    pass_marks: float
    negative_marking: float
    max_attempts: int
    shuffle_questions: bool
    show_review: bool
    start_at: datetime
    end_at: datetime
    status: ExamStatus
    task_points: Optional[int] = None
    course_title: Optional[str] = None
    questions_count: int = 0
    created_at: datetime
    updated_at: datetime


class ExamDetailResponse(ExamResponse):
    questions: List[QuestionResponse] = []


class StartAttemptResponse(BaseModel):
    attempt_id: uuid.UUID
    exam_id: uuid.UUID
    attempt_no: int
    started_at: datetime
    expires_at: datetime
    questions: List[QuestionResponse]


class AutosaveAnswerRequest(BaseModel):
    selected_option_id: Optional[uuid.UUID] = None


class AutosaveAnswerResponse(BaseModel):
    saved: bool = True
    server_time: datetime


class SubmitAttemptResponse(BaseModel):
    result_id: uuid.UUID
    attempt_id: uuid.UUID
    exam_id: uuid.UUID
    score: float
    total_marks: float
    percentage: float
    passed: bool
    grade: str
    rank_in_exam: Optional[int] = None
    task_points_awarded: int = 0
