from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import fitz  # type: ignore[import-untyped]

from app.models.document import (
    DocumentPageKind,
    OcrStatus,
    TextExtractionMethod,
)


@dataclass(frozen=True, slots=True)
class PdfPageExtraction:
    page_number: int
    text: str
    character_count: int
    image_count: int
    page_kind: DocumentPageKind
    extraction_method: TextExtractionMethod
    ocr_status: OcrStatus


@dataclass(frozen=True, slots=True)
class PdfTocEntry:
    level: int
    title: str
    page_number: int


@dataclass(frozen=True, slots=True)
class PdfExtractionResult:
    text: str
    page_count: int
    pages: tuple[PdfPageExtraction, ...]
    toc: tuple[PdfTocEntry, ...]


def classify_page(
    text: str,
    image_count: int,
) -> tuple[DocumentPageKind, TextExtractionMethod, OcrStatus]:
    character_count = len(text.strip())

    if character_count == 0 and image_count > 0:
        return (
            DocumentPageKind.SCANNED,
            TextExtractionMethod.NONE,
            OcrStatus.REQUIRED,
        )
    if character_count == 0:
        return (
            DocumentPageKind.EMPTY,
            TextExtractionMethod.NONE,
            OcrStatus.NOT_REQUIRED,
        )
    if image_count > 0 and character_count < 120:
        return (
            DocumentPageKind.MIXED,
            TextExtractionMethod.NATIVE,
            OcrStatus.REQUIRED,
        )
    return (
        DocumentPageKind.TEXTUAL,
        TextExtractionMethod.NATIVE,
        OcrStatus.NOT_REQUIRED,
    )


def _extract_pdf_sync(path: Path) -> PdfExtractionResult:
    full_text: list[str] = []
    extracted_pages: list[PdfPageExtraction] = []

    with fitz.open(path) as document:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            image_count = len(page.get_images(full=True))
            page_kind, extraction_method, ocr_status = classify_page(
                text,
                image_count,
            )
            extracted_pages.append(
                PdfPageExtraction(
                    page_number=page_number,
                    text=text,
                    character_count=len(text),
                    image_count=image_count,
                    page_kind=page_kind,
                    extraction_method=extraction_method,
                    ocr_status=ocr_status,
                )
            )
            if text:
                full_text.append(f"--- Página {page_number} ---\n{text}")

        toc_entries = tuple(
            PdfTocEntry(
                level=int(level),
                title=str(title).strip(),
                page_number=int(page_number),
            )
            for level, title, page_number, *_ in document.get_toc(simple=True)
            if str(title).strip() and 1 <= int(page_number) <= document.page_count
        )

        return PdfExtractionResult(
            text="\n\n".join(full_text).strip(),
            page_count=document.page_count,
            pages=tuple(extracted_pages),
            toc=toc_entries,
        )


async def extract_pdf(path: Path) -> PdfExtractionResult:
    return await asyncio.to_thread(_extract_pdf_sync, path)
