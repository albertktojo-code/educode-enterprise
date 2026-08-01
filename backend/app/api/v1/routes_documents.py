from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.auth import Membership, OrganizationRole
from app.models.document import (
    ChapterDetectionMethod,
    Document,
    DocumentChapter,
    DocumentPage,
    DocumentPageKind,
    DocumentStatus,
    OcrStatus,
)
from app.models.education import Project
from app.schemas.document import (
    ChapterDetectionRequest,
    ChapterTextPreview,
    DocumentChapterCreate,
    DocumentChapterRead,
    DocumentChapterUpdate,
    DocumentDetail,
    DocumentPageDetail,
    DocumentPageListItem,
    DocumentRead,
    DocumentStructureSummary,
    DocumentTextPreview,
    DocumentUpdate,
)
from app.services.documents.chapter_detector import detect_chapters
from app.services.documents.pdf_extractor import PdfExtractionResult, extract_pdf
from app.services.documents.storage import DocumentStorage, InvalidDocumentError

router = APIRouter(prefix="/documents", tags=["Documentos"])
settings = get_settings()
storage = DocumentStorage(
    root=settings.document_storage_path,
    max_size_bytes=settings.max_document_size_mb * 1024 * 1024,
)

READ_ROLES = (
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.TEACHER,
    OrganizationRole.MEMBER,
)
WRITE_ROLES = (
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.TEACHER,
)
ADMIN_ROLES = (OrganizationRole.OWNER, OrganizationRole.ADMIN)


def organization_id(membership: Membership) -> UUID:
    return membership.organization_id


async def get_document_in_organization(
    document_id: UUID,
    membership: Membership,
    session: AsyncSession,
) -> Document:
    document = await session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.organization_id == organization_id(membership),
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return document


async def get_chapter_in_document(
    chapter_id: UUID,
    document: Document,
    session: AsyncSession,
) -> DocumentChapter:
    chapter = await session.scalar(
        select(DocumentChapter).where(
            DocumentChapter.id == chapter_id,
            DocumentChapter.document_id == document.id,
        )
    )
    if chapter is None:
        raise HTTPException(status_code=404, detail="Capítulo não encontrado")
    return chapter


async def validate_project(
    project_id: UUID | None,
    membership: Membership,
    session: AsyncSession,
) -> None:
    if project_id is None:
        return
    project = await session.scalar(
        select(Project.id).where(
            Project.id == project_id,
            Project.organization_id == organization_id(membership),
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")


def validate_page_range(
    document: Document,
    start_page: int,
    end_page: int,
) -> None:
    page_count = document.page_count or 0
    if page_count <= 0:
        raise HTTPException(
            status_code=409,
            detail="O PDF precisa ser processado antes da criação de capítulos",
        )
    if start_page < 1 or end_page < start_page or end_page > page_count:
        raise HTTPException(
            status_code=422,
            detail=f"Intervalo inválido. O documento possui {page_count} página(s)",
        )


async def validate_confirmed_overlap(
    document: Document,
    start_page: int,
    end_page: int,
    session: AsyncSession,
    ignored_chapter_id: UUID | None = None,
) -> None:
    query = select(DocumentChapter.id).where(
        DocumentChapter.document_id == document.id,
        DocumentChapter.is_confirmed.is_(True),
        DocumentChapter.start_page <= end_page,
        DocumentChapter.end_page >= start_page,
    )
    if ignored_chapter_id is not None:
        query = query.where(DocumentChapter.id != ignored_chapter_id)
    if await session.scalar(query) is not None:
        raise HTTPException(
            status_code=409,
            detail="O intervalo se sobrepõe a outro capítulo confirmado",
        )


async def save_extraction(
    document: Document,
    result: PdfExtractionResult,
    session: AsyncSession,
    replace_structure: bool,
) -> None:
    await session.execute(delete(DocumentPage).where(DocumentPage.document_id == document.id))
    session.add_all(
        [
            DocumentPage(
                document_id=document.id,
                page_number=page.page_number,
                text=page.text,
                character_count=page.character_count,
                image_count=page.image_count,
                page_kind=page.page_kind,
                extraction_method=page.extraction_method,
                ocr_status=page.ocr_status,
            )
            for page in result.pages
        ]
    )

    if replace_structure:
        await session.execute(
            delete(DocumentChapter).where(DocumentChapter.document_id == document.id)
        )
    else:
        await session.execute(
            delete(DocumentChapter).where(
                DocumentChapter.document_id == document.id,
                DocumentChapter.is_confirmed.is_(False),
                DocumentChapter.detection_method != ChapterDetectionMethod.MANUAL,
            )
        )
    await session.flush()

    preserved = list(
        (
            await session.scalars(
                select(DocumentChapter).where(DocumentChapter.document_id == document.id)
            )
        ).all()
    )
    detected = detect_chapters(result.pages, result.toc, result.page_count)
    for candidate in detected:
        overlaps_preserved = any(
            chapter.start_page <= candidate.end_page and chapter.end_page >= candidate.start_page
            for chapter in preserved
        )
        if overlaps_preserved:
            continue
        session.add(
            DocumentChapter(
                document_id=document.id,
                title=candidate.title,
                chapter_number=candidate.chapter_number,
                start_page=candidate.start_page,
                end_page=candidate.end_page,
                detection_method=candidate.detection_method,
                confidence=candidate.confidence,
                is_confirmed=False,
                position=candidate.position,
            )
        )

    document.extracted_text = result.text
    document.page_count = result.page_count
    document.status = DocumentStatus.READY
    document.extraction_error = None
    document.processed_at = datetime.now(UTC)


async def process_document(
    document: Document,
    session: AsyncSession,
    replace_structure: bool = False,
) -> Document:
    document_id = document.id
    document.status = DocumentStatus.PROCESSING
    document.extraction_error = None
    await session.commit()

    try:
        result = await extract_pdf(storage.resolve(document.storage_key))
        await save_extraction(document, result, session, replace_structure)
        await session.commit()
        await session.refresh(document)
        return document
    except Exception as exc:
        await session.rollback()
        failed_document = await session.scalar(select(Document).where(Document.id == document_id))
        if failed_document is None:
            raise
        failed_document.status = DocumentStatus.FAILED
        failed_document.extraction_error = str(exc)[:4000]
        failed_document.processed_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(failed_document)
        return failed_document


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    status_filter: DocumentStatus | None = Query(default=None, alias="status"),
    project_id: UUID | None = None,
    search: str | None = None,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[Document]:
    query = select(Document).where(Document.organization_id == organization_id(membership))
    if status_filter is not None:
        query = query.where(Document.status == status_filter)
    if project_id is not None:
        query = query.where(Document.project_id == project_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Document.original_filename.ilike(term),
                Document.checksum_sha256.ilike(term),
            )
        )
    result = await session.scalars(query.order_by(Document.created_at.desc()))
    return list(result.all())


@router.post("/upload", response_model=DocumentDetail, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    project_id: UUID | None = Form(default=None),
    auto_process: bool = Form(default=True),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Document:
    await validate_project(project_id, membership, session)

    try:
        stored = await storage.save_pdf(file, organization_id(membership))
    except InvalidDocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    document = Document(
        organization_id=organization_id(membership),
        uploaded_by_id=membership.user_id,
        project_id=project_id,
        original_filename=(file.filename or "documento.pdf").strip(),
        storage_key=stored.storage_key,
        mime_type="application/pdf",
        size_bytes=stored.size_bytes,
        checksum_sha256=stored.checksum_sha256,
        status=DocumentStatus.UPLOADED,
    )
    session.add(document)
    try:
        await session.commit()
        await session.refresh(document)
    except Exception:
        await session.rollback()
        storage.delete(stored.storage_key)
        raise

    if auto_process:
        return await process_document(document, session)
    return document


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> Document:
    return await get_document_in_organization(document_id, membership, session)


@router.get("/{document_id}/text", response_model=DocumentTextPreview)
async def get_document_text(
    document_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> DocumentTextPreview:
    document = await get_document_in_organization(document_id, membership, session)
    text = document.extracted_text or ""
    return DocumentTextPreview(
        document_id=document.id,
        text=text,
        character_count=len(text),
        page_count=document.page_count,
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> FileResponse:
    document = await get_document_in_organization(document_id, membership, session)
    path: Path = storage.resolve(document.storage_key)
    if not await asyncio.to_thread(path.exists):
        raise HTTPException(status_code=404, detail="Arquivo físico não encontrado")
    return FileResponse(
        path,
        media_type=document.mime_type,
        filename=document.original_filename,
    )


@router.patch("/{document_id}", response_model=DocumentRead)
async def update_document(
    document_id: UUID,
    data: DocumentUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Document:
    document = await get_document_in_organization(document_id, membership, session)
    await validate_project(data.project_id, membership, session)
    document.project_id = data.project_id
    await session.commit()
    await session.refresh(document)
    return document


@router.post("/{document_id}/process", response_model=DocumentDetail)
async def reprocess_document(
    document_id: UUID,
    replace_structure: bool = False,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Document:
    document = await get_document_in_organization(document_id, membership, session)
    if document.status == DocumentStatus.PROCESSING:
        raise HTTPException(
            status_code=409,
            detail="O documento já está em processamento",
        )
    return await process_document(document, session, replace_structure)


@router.get(
    "/{document_id}/structure-summary",
    response_model=DocumentStructureSummary,
)
async def get_structure_summary(
    document_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> DocumentStructureSummary:
    document = await get_document_in_organization(document_id, membership, session)
    pages = list(
        (
            await session.scalars(
                select(DocumentPage).where(DocumentPage.document_id == document.id)
            )
        ).all()
    )
    chapters = list(
        (
            await session.scalars(
                select(DocumentChapter).where(DocumentChapter.document_id == document.id)
            )
        ).all()
    )
    return DocumentStructureSummary(
        document_id=document.id,
        page_count=document.page_count or 0,
        extracted_pages=len(pages),
        textual_pages=sum(page.page_kind == DocumentPageKind.TEXTUAL for page in pages),
        mixed_pages=sum(page.page_kind == DocumentPageKind.MIXED for page in pages),
        scanned_pages=sum(page.page_kind == DocumentPageKind.SCANNED for page in pages),
        empty_pages=sum(page.page_kind == DocumentPageKind.EMPTY for page in pages),
        ocr_required_pages=sum(page.ocr_status == OcrStatus.REQUIRED for page in pages),
        chapter_count=len(chapters),
        confirmed_chapters=sum(chapter.is_confirmed for chapter in chapters),
    )


@router.get("/{document_id}/pages", response_model=list[DocumentPageListItem])
async def list_document_pages(
    document_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[DocumentPageListItem]:
    document = await get_document_in_organization(document_id, membership, session)
    pages = list(
        (
            await session.scalars(
                select(DocumentPage)
                .where(DocumentPage.document_id == document.id)
                .order_by(DocumentPage.page_number)
            )
        ).all()
    )
    return [
        DocumentPageListItem(
            id=page.id,
            document_id=page.document_id,
            page_number=page.page_number,
            character_count=page.character_count,
            image_count=page.image_count,
            page_kind=page.page_kind,
            extraction_method=page.extraction_method,
            ocr_status=page.ocr_status,
            text_preview=(page.text[:500] + "…") if len(page.text) > 500 else page.text,
        )
        for page in pages
    ]


@router.get(
    "/{document_id}/pages/{page_number}",
    response_model=DocumentPageDetail,
)
async def get_document_page(
    document_id: UUID,
    page_number: int,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> DocumentPage:
    document = await get_document_in_organization(document_id, membership, session)
    page = await session.scalar(
        select(DocumentPage).where(
            DocumentPage.document_id == document.id,
            DocumentPage.page_number == page_number,
        )
    )
    if page is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    return page


@router.get(
    "/{document_id}/chapters",
    response_model=list[DocumentChapterRead],
)
async def list_document_chapters(
    document_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[DocumentChapter]:
    document = await get_document_in_organization(document_id, membership, session)
    chapters = await session.scalars(
        select(DocumentChapter)
        .where(DocumentChapter.document_id == document.id)
        .order_by(
            DocumentChapter.position,
            DocumentChapter.start_page,
            DocumentChapter.created_at,
        )
    )
    return list(chapters.all())


@router.post(
    "/{document_id}/chapters/detect",
    response_model=list[DocumentChapterRead],
)
async def redetect_document_chapters(
    document_id: UUID,
    data: ChapterDetectionRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> list[DocumentChapter]:
    document = await get_document_in_organization(document_id, membership, session)
    if document.status == DocumentStatus.PROCESSING:
        raise HTTPException(status_code=409, detail="Documento em processamento")

    result = await extract_pdf(storage.resolve(document.storage_key))
    if data.replace_all:
        await session.execute(
            delete(DocumentChapter).where(DocumentChapter.document_id == document.id)
        )
    else:
        await session.execute(
            delete(DocumentChapter).where(
                DocumentChapter.document_id == document.id,
                DocumentChapter.is_confirmed.is_(False),
                DocumentChapter.detection_method != ChapterDetectionMethod.MANUAL,
            )
        )
    await session.flush()

    preserved = list(
        (
            await session.scalars(
                select(DocumentChapter).where(DocumentChapter.document_id == document.id)
            )
        ).all()
    )
    for candidate in detect_chapters(result.pages, result.toc, result.page_count):
        if any(
            chapter.start_page <= candidate.end_page and chapter.end_page >= candidate.start_page
            for chapter in preserved
        ):
            continue
        session.add(
            DocumentChapter(
                document_id=document.id,
                title=candidate.title,
                chapter_number=candidate.chapter_number,
                start_page=candidate.start_page,
                end_page=candidate.end_page,
                detection_method=candidate.detection_method,
                confidence=candidate.confidence,
                is_confirmed=False,
                position=candidate.position,
            )
        )
    await session.commit()
    chapters = await session.scalars(
        select(DocumentChapter)
        .where(DocumentChapter.document_id == document.id)
        .order_by(DocumentChapter.position, DocumentChapter.start_page)
    )
    return list(chapters.all())


@router.post(
    "/{document_id}/chapters",
    response_model=DocumentChapterRead,
    status_code=201,
)
async def create_document_chapter(
    document_id: UUID,
    data: DocumentChapterCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> DocumentChapter:
    document = await get_document_in_organization(document_id, membership, session)
    validate_page_range(document, data.start_page, data.end_page)
    if data.is_confirmed:
        await validate_confirmed_overlap(
            document,
            data.start_page,
            data.end_page,
            session,
        )
    chapter = DocumentChapter(
        document_id=document.id,
        title=data.title.strip(),
        chapter_number=data.chapter_number,
        start_page=data.start_page,
        end_page=data.end_page,
        summary=data.summary.strip() if data.summary else None,
        detection_method=ChapterDetectionMethod.MANUAL,
        confidence=1.0,
        is_confirmed=data.is_confirmed,
        position=data.position,
    )
    session.add(chapter)
    await session.commit()
    await session.refresh(chapter)
    return chapter


@router.get(
    "/{document_id}/chapters/{chapter_id}/text",
    response_model=ChapterTextPreview,
)
async def get_chapter_text(
    document_id: UUID,
    chapter_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> ChapterTextPreview:
    document = await get_document_in_organization(document_id, membership, session)
    chapter = await get_chapter_in_document(chapter_id, document, session)
    pages = list(
        (
            await session.scalars(
                select(DocumentPage)
                .where(
                    DocumentPage.document_id == document.id,
                    DocumentPage.page_number >= chapter.start_page,
                    DocumentPage.page_number <= chapter.end_page,
                )
                .order_by(DocumentPage.page_number)
            )
        ).all()
    )
    text_parts = [f"--- Página {page.page_number} ---\n{page.text}" for page in pages if page.text]
    text = "\n\n".join(text_parts)
    return ChapterTextPreview(
        chapter=DocumentChapterRead.model_validate(chapter),
        text=text,
        character_count=len(text),
        source_pages=[page.page_number for page in pages],
    )


@router.patch(
    "/{document_id}/chapters/{chapter_id}",
    response_model=DocumentChapterRead,
)
async def update_document_chapter(
    document_id: UUID,
    chapter_id: UUID,
    data: DocumentChapterUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> DocumentChapter:
    document = await get_document_in_organization(document_id, membership, session)
    chapter = await get_chapter_in_document(chapter_id, document, session)

    start_page = data.start_page if data.start_page is not None else chapter.start_page
    end_page = data.end_page if data.end_page is not None else chapter.end_page
    validate_page_range(document, start_page, end_page)
    will_be_confirmed = data.is_confirmed if data.is_confirmed is not None else chapter.is_confirmed
    if will_be_confirmed:
        await validate_confirmed_overlap(
            document,
            start_page,
            end_page,
            session,
            ignored_chapter_id=chapter.id,
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in {"title", "summary"} and isinstance(value, str):
            value = value.strip() or None
        setattr(chapter, field, value)
    if data.title is not None and not chapter.title:
        raise HTTPException(status_code=422, detail="O título não pode ficar vazio")

    await session.commit()
    await session.refresh(chapter)
    return chapter


@router.delete("/{document_id}/chapters/{chapter_id}", status_code=204)
async def delete_document_chapter(
    document_id: UUID,
    chapter_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Response:
    document = await get_document_in_organization(document_id, membership, session)
    chapter = await get_chapter_in_document(chapter_id, document, session)
    await session.delete(chapter)
    await session.commit()
    return Response(status_code=204)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> Response:
    document = await get_document_in_organization(document_id, membership, session)
    storage_key = document.storage_key
    await session.delete(document)
    await session.commit()
    storage.delete(storage_key)
    return Response(status_code=204)
