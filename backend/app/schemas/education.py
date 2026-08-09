from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.education import ContentType, ProjectStatus


class SubjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=2, max_length=40)
    description: str | None = None


class SubjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    code: str | None = Field(default=None, min_length=2, max_length=40)
    description: str | None = None
    is_active: bool | None = None


class SubjectRead(SubjectCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    is_active: bool
    created_at: datetime


class ClassroomCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    subject_id: UUID | None = None
    school_unit_id: UUID | None = None
    school_year: int | None = Field(default=None, ge=2020, le=2100)
    grade: str | None = Field(default=None, max_length=60)
    shift: str | None = Field(default=None, max_length=30)
    description: str | None = None


class ClassroomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    subject_id: UUID | None = None
    school_unit_id: UUID | None = None
    school_year: int | None = Field(default=None, ge=2020, le=2100)
    grade: str | None = Field(default=None, max_length=60)
    shift: str | None = Field(default=None, max_length=30)
    description: str | None = None
    is_active: bool | None = None


class ClassroomRead(ClassroomCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    is_active: bool
    created_at: datetime


EnrollmentRole = Literal["student", "teacher", "assistant"]


class EnrollmentCreate(BaseModel):
    user_id: UUID
    role: EnrollmentRole = "student"


class EnrollmentRead(BaseModel):
    id: UUID
    classroom_id: UUID
    user_id: UUID
    full_name: str
    email: EmailStr
    role: EnrollmentRole
    created_at: datetime


class DirectoryUser(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    organization_role: str


class ProjectCreate(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    description: str | None = None
    classroom_id: UUID | None = None
    subject_id: UUID | None = None
    status: ProjectStatus = ProjectStatus.DRAFT


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=180)
    description: str | None = None
    classroom_id: UUID | None = None
    subject_id: UUID | None = None
    status: ProjectStatus | None = None


class ProjectRead(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime


class ContentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    content_type: ContentType
    body: str | None = None
    position: int = Field(default=0, ge=0)
    is_published: bool = False


class ContentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=180)
    content_type: ContentType | None = None
    body: str | None = None
    position: int | None = Field(default=None, ge=0)
    is_published: bool | None = None


class ContentRead(ContentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    created_at: datetime


class DashboardSummary(BaseModel):
    subjects: int
    classrooms: int
    active_classrooms: int
    users: int
    projects: int
    draft_projects: int
    active_projects: int
    archived_projects: int
    contents: int
    published_contents: int
    documents: int
    ready_documents: int
