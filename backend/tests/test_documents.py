from io import BytesIO
from pathlib import Path
from uuid import uuid4

import fitz
import pytest
from starlette.datastructures import Headers, UploadFile

from app.models.document import DocumentPageKind, OcrStatus, TextExtractionMethod
from app.services.documents.pdf_extractor import classify_page, extract_pdf
from app.services.documents.storage import DocumentStorage, InvalidDocumentError


def create_pdf(path: Path, text: str = "Pensamento Computacional") -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()


async def test_pdf_extraction_returns_pages_text_and_page_count(tmp_path: Path) -> None:
    pdf_path = tmp_path / "material.pdf"
    create_pdf(pdf_path)

    result = await extract_pdf(pdf_path)

    assert result.page_count == 1
    assert len(result.pages) == 1
    assert result.pages[0].page_number == 1
    assert result.pages[0].page_kind == DocumentPageKind.TEXTUAL
    assert "Pensamento Computacional" in result.text
    assert "Página 1" in result.text


def test_page_classification_prepares_ocr_only_when_needed() -> None:
    assert classify_page("Texto suficiente " * 20, 0) == (
        DocumentPageKind.TEXTUAL,
        TextExtractionMethod.NATIVE,
        OcrStatus.NOT_REQUIRED,
    )
    assert classify_page("", 1) == (
        DocumentPageKind.SCANNED,
        TextExtractionMethod.NONE,
        OcrStatus.REQUIRED,
    )
    assert classify_page("Legenda curta", 2) == (
        DocumentPageKind.MIXED,
        TextExtractionMethod.NATIVE,
        OcrStatus.REQUIRED,
    )
    assert classify_page("", 0) == (
        DocumentPageKind.EMPTY,
        TextExtractionMethod.NONE,
        OcrStatus.NOT_REQUIRED,
    )


async def test_storage_saves_valid_pdf_with_checksum(tmp_path: Path) -> None:
    source_path = tmp_path / "source.pdf"
    create_pdf(source_path, "EduCode Enterprise")
    upload = UploadFile(
        file=BytesIO(source_path.read_bytes()),
        filename="material.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )
    storage = DocumentStorage(tmp_path / "storage", max_size_bytes=5 * 1024 * 1024)

    stored = await storage.save_pdf(upload, uuid4())

    assert stored.size_bytes > 0
    assert len(stored.checksum_sha256) == 64
    assert storage.resolve(stored.storage_key).exists()


async def test_storage_rejects_non_pdf_content(tmp_path: Path) -> None:
    upload = UploadFile(
        file=BytesIO(b"not-a-pdf"),
        filename="material.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )
    storage = DocumentStorage(tmp_path / "storage", max_size_bytes=1024)

    with pytest.raises(InvalidDocumentError, match="não corresponde a um PDF"):
        await storage.save_pdf(upload, uuid4())
