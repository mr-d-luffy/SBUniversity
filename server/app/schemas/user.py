import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.db.models.user import UserRole, UserStatus, UserVerificationStatus


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str


class DepartmentCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=200)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) < 2:
            raise ValueError("Department code must contain at least 2 characters")
        return value

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Department name must contain at least 2 characters")
        return value


class StudentProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: uuid.UUID
    student_code: str
    department_id: Optional[uuid.UUID] = None
    department: Optional[DepartmentResponse] = None
    batch_year: Optional[int] = None
    academic_term: Optional[str] = None
    verification_status: UserVerificationStatus = UserVerificationStatus.NOT_VERIFIED
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    photo_path: Optional[str] = None
    id_valid_until: Optional[date] = None
    qr_token: str


class TeacherProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: uuid.UUID
    employee_code: str
    department_id: Optional[uuid.UUID] = None
    department: Optional[DepartmentResponse] = None
    verification_status: UserVerificationStatus = UserVerificationStatus.NOT_VERIFIED
    designation: Optional[str] = None
    bio: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    clerk_user_id: str
    email: EmailStr
    full_name: str
    avatar_url: Optional[str] = None
    role: UserRole
    status: UserStatus
    created_at: datetime
    student_profile: Optional[StudentProfileResponse] = None
    teacher_profile: Optional[TeacherProfileResponse] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    date_of_birth: Optional[date] = None


class RoleUpdateRequest(BaseModel):
    role: UserRole


class StatusUpdateRequest(BaseModel):
    status: UserStatus


class AdminUserAcademicUpdate(BaseModel):
    department_id: Optional[uuid.UUID] = None
    academic_term: Optional[str] = Field(default=None, max_length=100)
    verification_status: Optional[UserVerificationStatus] = None


class VirtualIDCardResponse(BaseModel):
    name: str
    student_code: str
    department: Optional[str] = None
    academic_term: Optional[str] = None
    verification_status: UserVerificationStatus = UserVerificationStatus.NOT_VERIFIED
    batch_year: Optional[int] = None
    phone: Optional[str] = None
    photo_url: Optional[str] = None
    valid_until: Optional[date] = None
    qr_verify_url: str
    status: str


class UserStatsResponse(BaseModel):
    total: int
    students: int
    teachers: int
    admins: int
