from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.services.object_storage import ObjectStoragePort

MIME_EXTENSIONS = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
}


class InvalidEnrollmentDocumentError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StoredEnrollmentDocument:
    storage_key: str
    original_filename: str
    content_type: str
    size_bytes: int
    checksum_sha256: str


def _validate_signature(content: bytes, content_type: str) -> None:
    signature = content[:12]
    valid = (
        content_type == "application/pdf"
        and signature.startswith(b"%PDF-")
        or content_type == "image/png"
        and signature.startswith(b"\x89PNG\r\n\x1a\n")
        or content_type == "image/jpeg"
        and signature.startswith(b"\xff\xd8\xff")
    )
    if not valid:
        raise InvalidEnrollmentDocumentError("O conteúdo não corresponde ao tipo de arquivo")


async def save_enrollment_document(
    storage: ObjectStoragePort,
    upload: UploadFile,
    *,
    organization_id: UUID,
    application_id: UUID,
    document_id: UUID,
    version_number: int,
    accepted_mime_types: list[str],
    max_size_bytes: int,
) -> StoredEnrollmentDocument:
    original_filename = Path((upload.filename or "").strip()).name
    if not original_filename:
        raise InvalidEnrollmentDocumentError("O arquivo precisa possuir um nome")
    content_type = (upload.content_type or "").lower()
    if content_type not in accepted_mime_types or content_type not in MIME_EXTENSIONS:
        raise InvalidEnrollmentDocumentError("Tipo de arquivo não permitido para este documento")
    suffix = Path(original_filename).suffix.lower()
    if suffix not in MIME_EXTENSIONS[content_type]:
        raise InvalidEnrollmentDocumentError("A extensão não corresponde ao tipo de arquivo")

    content = bytearray()
    try:
        while chunk := await upload.read(1024 * 1024):
            content.extend(chunk)
            if len(content) > max_size_bytes:
                limit_mb = max_size_bytes // (1024 * 1024)
                raise InvalidEnrollmentDocumentError(f"O arquivo excede o limite de {limit_mb} MB")
    finally:
        await upload.close()
    if not content:
        raise InvalidEnrollmentDocumentError("O arquivo enviado está vazio")
    _validate_signature(bytes(content), content_type)

    storage_key = (
        f"school-admissions/{organization_id}/{application_id}/"
        f"{document_id}/v{version_number}/{uuid4()}{suffix}"
    )
    metadata = await storage.put_bytes(storage_key, bytes(content), content_type)
    return StoredEnrollmentDocument(
        storage_key=storage_key,
        original_filename=original_filename[:255],
        content_type=content_type,
        size_bytes=metadata.size_bytes,
        checksum_sha256=metadata.checksum_sha256,
    )
