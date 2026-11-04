import uuid
from datetime import datetime
from decimal import Decimal
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
    price: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    discount_percent: int = Field(default=0, ge=0, le=100)


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    teacher_id: Optional[uuid.UUID] = None
    is_published: Optional[bool] = None
    price: Optional[Decimal] = Field(default=None, ge=0, decimal_places=2)
    discount_percent: Optional[int] = Field(default=None, ge=0, le=100)


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    title: str
    description: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    teacher_id: uuid.UUID
    is_published: bool
    price: float
    discount_percent: int
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
    price: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    discount_percent: int = Field(default=0, ge=0, le=100)


class AdminCourseUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=2, max_length=50)
    title: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    teacher_ids: Optional[list[uuid.UUID]] = None
    student_ids: Optional[list[uuid.UUID]] = None
    is_published: Optional[bool] = None
    enroll_all_active_students: Optional[bool] = None
    price: Optional[Decimal] = Field(default=None, ge=0, decimal_places=2)
    discount_percent: Optional[int] = Field(default=None, ge=0, le=100)


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


class CoursePricingUpdate(BaseModel):
    price: Decimal = Field(ge=0, decimal_places=2)
    discount_percent: int = Field(ge=0, le=100)


class CourseKeyActivationRequest(BaseModel):
    key: str = Field(pattern=r"^SB-[A-Z2-9]{5}-[A-Z2-9]{5}$")


class StudentCourseKeyRequestResponse(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    course_title: str
    status: str
    requested_at: datetime
    reviewed_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None


class AdminCourseKeyRequestResponse(StudentCourseKeyRequestResponse):
    student_id: uuid.UUID
    student_name: str
    student_email: str
    access_key: Optional[str] = None
