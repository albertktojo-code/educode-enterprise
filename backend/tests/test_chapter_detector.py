from app.models.document import (
    ChapterDetectionMethod,
    DocumentPageKind,
    OcrStatus,
    TextExtractionMethod,
)
from app.services.documents.chapter_detector import detect_chapters
from app.services.documents.pdf_extractor import PdfPageExtraction, PdfTocEntry


def page(number: int, text: str) -> PdfPageExtraction:
    return PdfPageExtraction(
        page_number=number,
        text=text,
        character_count=len(text),
        image_count=0,
        page_kind=DocumentPageKind.TEXTUAL,
        extraction_method=TextExtractionMethod.NATIVE,
        ocr_status=OcrStatus.NOT_REQUIRED,
    )


def test_chapters_prefer_pdf_toc() -> None:
    pages = tuple(page(number, f"Texto da página {number}") for number in range(1, 11))
    toc = (
        PdfTocEntry(level=1, title="Números", page_number=1),
        PdfTocEntry(level=2, title="Números naturais", page_number=2),
        PdfTocEntry(level=1, title="Frações", page_number=6),
    )

    chapters = detect_chapters(pages, toc, 10)

    assert [chapter.title for chapter in chapters] == ["Números", "Frações"]
    assert chapters[0].start_page == 1
    assert chapters[0].end_page == 5
    assert chapters[1].end_page == 10
    assert chapters[0].detection_method == ChapterDetectionMethod.PDF_TOC


def test_chapters_fallback_to_heading_detection() -> None:
    pages = (
        page(1, "CAPÍTULO 1 - NÚMEROS NATURAIS\nConteúdo introdutório"),
        page(2, "Exercícios e exemplos"),
        page(3, "CAPÍTULO 2 - FRAÇÕES\nConceitos de fração"),
        page(4, "Problemas com frações"),
    )

    chapters = detect_chapters(pages, (), 4)

    assert len(chapters) == 2
    assert chapters[0].start_page == 1
    assert chapters[0].end_page == 2
    assert chapters[1].start_page == 3
    assert chapters[1].end_page == 4
    assert chapters[0].detection_method == ChapterDetectionMethod.AUTOMATIC_HEADING
