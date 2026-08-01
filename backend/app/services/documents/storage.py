from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile


@dataclass(frozen=True, slots=True)
class StoredDocument:
    storage_key: str
    size_bytes: int
    checksum_sha256: str


class InvalidDocumentError(ValueError):
    """Raised when an uploaded document violates validation rules."""


class DocumentStorage:
    def __init__(self, root: str | Path, max_size_bytes: int) -> None:
        self.root = Path(root).resolve()
        self.max_size_bytes = max_size_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    async def save_pdf(self, upload: UploadFile, organization_id: UUID) -> StoredDocument:
        filename = (upload.filename or "").strip()
        if not filename.lower().endswith(".pdf"):
            raise InvalidDocumentError("Envie um arquivo com extensão .pdf")

        content_type = (upload.content_type or "").lower()
        if content_type not in {"application/pdf", "application/octet-stream", ""}:
            raise InvalidDocumentError("O arquivo enviado não possui um tipo PDF válido")

        organization_folder = self.root / str(organization_id)
        organization_folder.mkdir(parents=True, exist_ok=True)
        storage_key = f"{organization_id}/{uuid4()}.pdf"
        destination = self.resolve(storage_key)

        digest = hashlib.sha256()
        total = 0

        try:
            with destination.open("wb") as target:
                while chunk := await upload.read(1024 * 1024):
                    total += len(chunk)
                    if total > self.max_size_bytes:
                        raise InvalidDocumentError(
                            f"O PDF excede o limite de {self.max_size_bytes // (1024 * 1024)} MB"
                        )
                    digest.update(chunk)
                    target.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

        if total == 0:
            destination.unlink(missing_ok=True)
            raise InvalidDocumentError("O arquivo enviado está vazio")

        with destination.open("rb") as source:
            if source.read(5) != b"%PDF-":
                destination.unlink(missing_ok=True)
                raise InvalidDocumentError("O conteúdo do arquivo não corresponde a um PDF")

        return StoredDocument(
            storage_key=storage_key,
            size_bytes=total,
            checksum_sha256=digest.hexdigest(),
        )

    def resolve(self, storage_key: str) -> Path:
        candidate = (self.root / storage_key).resolve()
        if self.root not in candidate.parents:
            raise InvalidDocumentError("Chave de armazenamento inválida")
        return candidate

    def delete(self, storage_key: str) -> None:
        self.resolve(storage_key).unlink(missing_ok=True)
