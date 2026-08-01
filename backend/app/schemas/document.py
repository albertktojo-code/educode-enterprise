from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.document import (
    ChapterDetectionMethod,
    DocumentPageKind,
    DocumentStatus,
    OcrStatus,
    TextExtractionMethod,
)


class DocumentUpdate(BaseModel):
    project_id: UUID | None = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    uploaded_by_id: UUID
    project_id: UUID | None
    original_filename: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str
    status: DocumentStatus
    page_count: int | None
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None


class DocumentDetail(DocumentRead):
    extracted_text: str | None
    extraction_error: str | None


class DocumentTextPreview(BaseModel):
    document_id: UUID
    text: str = Field(default="")
    character_count: int
    page_count: int | None


class DocumentPageListItem(BaseModel):
    id: UUID
    document_id: UUID
    page_number: int
    character_count: int
    image_count: int
    page_kind: DocumentPageKind
    extraction_method: TextExtractionMethod
    ocr_status: OcrStatus
    text_preview: str


class DocumentPageDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    page_number: int
    text: str
    character_count: int
    image_count: int
    page_kind: DocumentPageKind
    extraction_method: TextExtractionMethod
    ocr_status: OcrStatus
    created_at: datetime
    updated_at: datetime


class DocumentChapterBase(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    chapter_number: int | None = Field(default=None, ge=1)
    start_page: int = Field(ge=1)
    end_page: int = Field(ge=1)
    summary: str | None = Field(default=None, max_length=6000)
    is_confirmed: bool = False
    position: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_page_range(self) -> "DocumentChapterBase":
        if self.end_page < self.start_page:
            raise ValueError("A página final deve ser maior ou igual à página inicial")
        return self


class DocumentChapterCreate(DocumentChapterBase):
    pass


class DocumentChapterUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=240)
    chapter_number: int | None = Field(default=None, ge=1)
    start_page: int | None = Field(default=None, ge=1)
    end_page: int | None = Field(default=None, ge=1)
    summary: str | None = Field(default=None, max_length=6000)
    is_confirmed: bool | None = None
    position: int | None = Field(default=None, ge=0)


class DocumentChapterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    title: str
    chapter_number: int | None
    start_page: int
    end_page: int
    summary: str | None
    detection_method: ChapterDetectionMethod
    confidence: float
    is_confirmed: bool
    position: int
    created_at: datetime
    updated_at: datetime


class ChapterDetectionRequest(BaseModel):
    replace_all: bool = False


class ChapterTextPreview(BaseModel):
    chapter: DocumentChapterRead
    text: str
    character_count: int
    source_pages: list[int]


class DocumentStructureSummary(BaseModel):
    document_id: UUID
    page_count: int
    extracted_pages: int
    textual_pages: int
    mixed_pages: int
    scanned_pages: int
    empty_pages: int
    ocr_required_pages: int
    chapter_count: int
    confirmed_chapters: int
