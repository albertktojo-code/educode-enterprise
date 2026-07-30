from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from app.models.document import ChapterDetectionMethod
from app.services.documents.pdf_extractor import PdfPageExtraction, PdfTocEntry


@dataclass(frozen=True, slots=True)
class DetectedChapter:
    title: str
    chapter_number: int | None
    start_page: int
    end_page: int
    detection_method: ChapterDetectionMethod
    confidence: float
    position: int


_EXPLICIT_HEADING = re.compile(
    r"^(?:cap[ií]tulo|unidade|m[oó]dulo|se[cç][aã]o)\s+"
    r"(?P<number>\d+|[ivxlcdm]+)\s*[:\-–—]?\s*(?P<title>.*)$",
    re.IGNORECASE,
)
_NUMBERED_HEADING = re.compile(r"^(?P<number>\d{1,3})(?:\.\d+)*\s*[:\-–—.]\s+(?P<title>.{3,120})$")


def _clean_title(value: str) -> str:
    return " ".join(value.replace("\u00a0", " ").split()).strip(" -–—:.")


def _roman_or_int(value: str) -> int | None:
    if value.isdigit():
        return int(value)
    roman_values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    previous = 0
    for symbol in reversed(value.upper()):
        current = roman_values.get(symbol)
        if current is None:
            return None
        total += -current if current < previous else current
        previous = max(previous, current)
    return total or None


def _chapters_from_toc(
    toc: tuple[PdfTocEntry, ...],
    page_count: int,
) -> list[DetectedChapter]:
    if not toc:
        return []

    top_level = min(entry.level for entry in toc)
    selected = [entry for entry in toc if entry.level == top_level]
    unique: list[PdfTocEntry] = []
    seen: set[tuple[str, int]] = set()
    for entry in selected:
        key = (_clean_title(entry.title).lower(), entry.page_number)
        if key in seen:
            continue
        seen.add(key)
        unique.append(entry)

    chapters: list[DetectedChapter] = []
    for index, entry in enumerate(unique):
        end_page = unique[index + 1].page_number - 1 if index + 1 < len(unique) else page_count
        title = _clean_title(entry.title) or f"Capítulo {index + 1}"
        chapters.append(
            DetectedChapter(
                title=title,
                chapter_number=index + 1,
                start_page=entry.page_number,
                end_page=max(entry.page_number, end_page),
                detection_method=ChapterDetectionMethod.PDF_TOC,
                confidence=0.98,
                position=index,
            )
        )
    return chapters


def _heading_candidate(page: PdfPageExtraction) -> tuple[str, int | None, float] | None:
    if not page.text:
        return None

    lines = [_clean_title(line) for line in page.text.splitlines() if _clean_title(line)]
    for line in lines[:14]:
        if len(line) > 140:
            continue
        explicit = _EXPLICIT_HEADING.match(line)
        if explicit:
            suffix = _clean_title(explicit.group("title"))
            number_text = explicit.group("number")
            number = _roman_or_int(number_text)
            prefix = line[: explicit.start("title")].strip(" -–—:.")
            title = f"{prefix}: {suffix}" if suffix else prefix
            return _clean_title(title), number, 0.86

        numbered = _NUMBERED_HEADING.match(line)
        if numbered:
            return (
                _clean_title(line),
                int(numbered.group("number")),
                0.70,
            )

        letters = [character for character in line if character.isalpha()]
        if (
            5 <= len(line) <= 90
            and len(letters) >= 4
            and line.upper() == line
            and not line.endswith(".")
        ):
            return line.title(), None, 0.58
    return None


def _chapters_from_headings(
    pages: tuple[PdfPageExtraction, ...],
    page_count: int,
) -> list[DetectedChapter]:
    raw: list[tuple[int, str, int | None, float]] = []
    for page in pages:
        candidate = _heading_candidate(page)
        if candidate is None:
            continue
        title, number, confidence = candidate
        raw.append((page.page_number, title, number, confidence))

    repeated = Counter(title.lower() for _, title, _, _ in raw)
    candidates: list[tuple[int, str, int | None, float]] = []
    seen_pages: set[int] = set()
    for raw_candidate in raw:
        page_number, title, _, confidence = raw_candidate
        if page_number in seen_pages:
            continue
        if repeated[title.lower()] > 2 and confidence < 0.8:
            continue
        seen_pages.add(page_number)
        candidates.append(raw_candidate)

    if not candidates:
        return [
            DetectedChapter(
                title="Conteúdo completo",
                chapter_number=1,
                start_page=1,
                end_page=max(1, page_count),
                detection_method=ChapterDetectionMethod.AUTOMATIC_HEADING,
                confidence=0.35,
                position=0,
            )
        ]

    chapters: list[DetectedChapter] = []
    for index, (start_page, title, number, confidence) in enumerate(candidates):
        end_page = candidates[index + 1][0] - 1 if index + 1 < len(candidates) else page_count
        chapters.append(
            DetectedChapter(
                title=title,
                chapter_number=number or index + 1,
                start_page=start_page,
                end_page=max(start_page, end_page),
                detection_method=ChapterDetectionMethod.AUTOMATIC_HEADING,
                confidence=confidence,
                position=index,
            )
        )
    return chapters


def detect_chapters(
    pages: tuple[PdfPageExtraction, ...],
    toc: tuple[PdfTocEntry, ...],
    page_count: int,
) -> list[DetectedChapter]:
    toc_chapters = _chapters_from_toc(toc, page_count)
    if toc_chapters:
        return toc_chapters
    return _chapters_from_headings(pages, page_count)
