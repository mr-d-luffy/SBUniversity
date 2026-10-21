import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.course import EnrollmentStatus


class CourseCreate(BaseModel):
    code: str
    title: str
    description: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    teacher_id: Optional[uuid.UUID] = None  # Admin can specify, teacher defaults to self
    is_published: bool = False


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    teacher_id: Optional[uuid.UUID] = None
    is_published: Optional[bool] = None


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    title: str
    description: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    teacher_id: uuid.UUID
    is_published: bool
    created_at: datetime
    updated_at: datetime


class EnrollmentCreate(BaseModel):
    student_id: uuid.UUID
    course_id: uuid.UUID


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    course: Optional[CourseResponse] = None
    status: EnrollmentStatus
    progress_percent: float
    enrolled_at: datetime
    completed_at: Optional[datetime] = None


class AdminCourseCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=2, max_length=200)
    description: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    teacher_id: Optional[uuid.UUID] = None
    teacher_ids: list[uuid.UUID] = Field(default_factory=list)
    student_ids: list[uuid.UUID] = Field(default_factory=list)
    is_published: bool = True
    enroll_all_active_students: bool = True


class AdminCourseUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=2, max_length=50)
    title: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    teacher_ids: Optional[list[uuid.UUID]] = None
    student_ids: Optional[list[uuid.UUID]] = None
    is_published: Optional[bool] = None
    enroll_all_active_students: Optional[bool] = None


class AdminCourseResponse(CourseResponse):
    enrolled_students: int = 0
    teacher_ids: list[uuid.UUID] = Field(default_factory=list)
    student_ids: list[uuid.UUID] = Field(default_factory=list)


class AdminTeacherResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str


class AdminStudentResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    is_active: bool


class AdminCourseTeacherUpdate(BaseModel):
    teacher_id: uuid.UUID
