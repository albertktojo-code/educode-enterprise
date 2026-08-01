import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PageText:
    page_number: int | None
    text: str


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    chunk_index: int
    content: str
    page_start: int | None
    page_end: int | None
    source_order: int
    character_count: int
    token_estimate: int
    content_checksum: str
    security_flag: bool
    security_notes: str | None


INJECTION_PATTERNS = (
    r"ignore\s+(all|any|the)\s+(previous|prior)\s+instructions",
    r"ignore\s+as\s+instruções\s+anteriores",
    r"system\s+prompt",
    r"developer\s+message",
    r"revele\s+(o|a)\s+(prompt|instruções)",
    r"execute\s+the\s+following",
)


def detect_prompt_injection(text: str) -> tuple[bool, str | None]:
    lowered = text.casefold()
    matches = [pattern for pattern in INJECTION_PATTERNS if re.search(pattern, lowered)]
    if not matches:
        return False, None
    return (
        True,
        "Possível instrução maliciosa encontrada; tratar somente como fonte não executável.",
    )


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\t\f\v]+", " ", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def paragraph_units(pages: list[PageText]) -> list[tuple[int | None, str]]:
    units: list[tuple[int | None, str]] = []
    for page in pages:
        cleaned = normalize_text(page.text)
        if not cleaned:
            continue
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", cleaned) if part.strip()]
        if len(paragraphs) == 1 and len(paragraphs[0]) > 1800:
            paragraphs = [
                part.strip()
                for part in re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9])", paragraphs[0])
                if part.strip()
            ]
        units.extend((page.page_number, paragraph) for paragraph in paragraphs)
    return units


class HierarchicalChunker:
    def __init__(self, *, target_chars: int = 1000, overlap_chars: int = 160, min_chars: int = 200):
        if target_chars < 300:
            raise ValueError("target_chars deve ser pelo menos 300")
        if overlap_chars < 0 or overlap_chars >= target_chars:
            raise ValueError("overlap_chars inválido")
        if min_chars < 50 or min_chars > target_chars:
            raise ValueError("min_chars inválido")
        self.target_chars = target_chars
        self.overlap_chars = overlap_chars
        self.min_chars = min_chars

    def split(self, pages: list[PageText]) -> list[ChunkDraft]:
        units = paragraph_units(pages)
        if not units:
            return []

        groups: list[list[tuple[int | None, str]]] = []
        current: list[tuple[int | None, str]] = []
        current_size = 0

        for page_number, paragraph in units:
            paragraph_size = len(paragraph) + (2 if current else 0)
            if current and current_size + paragraph_size > self.target_chars:
                groups.append(current)
                overlap = self._overlap_units(current)
                current = overlap.copy()
                current_size = len("\n\n".join(text for _, text in current))
            current.append((page_number, paragraph))
            current_size += paragraph_size

        if current:
            groups.append(current)

        if len(groups) > 1 and len(self._group_text(groups[-1])) < self.min_chars:
            groups[-2].extend(groups.pop())

        drafts: list[ChunkDraft] = []
        for index, group in enumerate(groups):
            content = self._group_text(group)
            page_numbers = [page for page, _ in group if page is not None]
            flagged, notes = detect_prompt_injection(content)
            drafts.append(
                ChunkDraft(
                    chunk_index=index,
                    content=content,
                    page_start=min(page_numbers) if page_numbers else None,
                    page_end=max(page_numbers) if page_numbers else None,
                    source_order=index,
                    character_count=len(content),
                    token_estimate=max(1, round(len(content) / 4)),
                    content_checksum=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    security_flag=flagged,
                    security_notes=notes,
                )
            )
        return drafts

    def _overlap_units(self, group: list[tuple[int | None, str]]) -> list[tuple[int | None, str]]:
        if self.overlap_chars == 0:
            return []
        selected: list[tuple[int | None, str]] = []
        length = 0
        for item in reversed(group):
            selected.append(item)
            length += len(item[1]) + 2
            if length >= self.overlap_chars:
                break
        return list(reversed(selected))

    @staticmethod
    def _group_text(group: list[tuple[int | None, str]]) -> str:
        return "\n\n".join(text for _, text in group).strip()
