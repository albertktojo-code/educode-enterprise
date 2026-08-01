from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile

ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "application/pdf",
    "application/octet-stream",
}
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}


@dataclass(frozen=True, slots=True)
class StoredCreativeAsset:
    storage_key: str
    size_bytes: int
    checksum_sha256: str
    mime_type: str


class InvalidCreativeAssetError(ValueError):
    """Raised when an uploaded creative asset is invalid."""


class CreativeStorage:
    def __init__(self, root: str | Path, max_size_bytes: int) -> None:
        self.root = Path(root).resolve()
        self.max_size_bytes = max_size_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    async def save(self, upload: UploadFile, organization_id: UUID) -> StoredCreativeAsset:
        filename = (upload.filename or "").strip()
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise InvalidCreativeAssetError("Envie uma imagem PNG/JPG/WebP ou uma ficha em PDF")

        content_type = (upload.content_type or "application/octet-stream").lower()
        if content_type not in ALLOWED_MIME_TYPES:
            raise InvalidCreativeAssetError("Tipo de arquivo não permitido")

        folder = self.root / str(organization_id)
        folder.mkdir(parents=True, exist_ok=True)
        storage_key = f"{organization_id}/{uuid4()}{suffix}"
        destination = self.resolve(storage_key)
        digest = hashlib.sha256()
        total = 0

        try:
            with destination.open("wb") as target:
                while chunk := await upload.read(1024 * 1024):
                    total += len(chunk)
                    if total > self.max_size_bytes:
                        limit_mb = self.max_size_bytes // (1024 * 1024)
                        raise InvalidCreativeAssetError(
                            f"O arquivo excede o limite de {limit_mb} MB"
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
            raise InvalidCreativeAssetError("O arquivo enviado está vazio")

        signature = destination.read_bytes()[:12]
        if suffix == ".pdf" and not signature.startswith(b"%PDF-"):
            destination.unlink(missing_ok=True)
            raise InvalidCreativeAssetError("O conteúdo não corresponde a um PDF")
        if suffix == ".png" and not signature.startswith(b"\x89PNG\r\n\x1a\n"):
            destination.unlink(missing_ok=True)
            raise InvalidCreativeAssetError("O conteúdo não corresponde a uma imagem PNG")
        if suffix in {".jpg", ".jpeg"} and not signature.startswith(b"\xff\xd8\xff"):
            destination.unlink(missing_ok=True)
            raise InvalidCreativeAssetError("O conteúdo não corresponde a uma imagem JPEG")
        if suffix == ".webp" and not (signature.startswith(b"RIFF") and signature[8:12] == b"WEBP"):
            destination.unlink(missing_ok=True)
            raise InvalidCreativeAssetError("O conteúdo não corresponde a uma imagem WebP")

        normalized_mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".pdf": "application/pdf",
        }[suffix]
        return StoredCreativeAsset(
            storage_key=storage_key,
            size_bytes=total,
            checksum_sha256=digest.hexdigest(),
            mime_type=normalized_mime,
        )

    def resolve(self, storage_key: str) -> Path:
        candidate = (self.root / storage_key).resolve()
        if self.root not in candidate.parents:
            raise InvalidCreativeAssetError("Chave de armazenamento inválida")
        return candidate

    def delete(self, storage_key: str) -> None:
        self.resolve(storage_key).unlink(missing_ok=True)
