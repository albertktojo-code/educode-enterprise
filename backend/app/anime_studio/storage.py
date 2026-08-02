from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile

MEDIA_TYPES: dict[str, tuple[set[str], set[str]]] = {
    "image": (
        {".png", ".jpg", ".jpeg", ".webp"},
        {"image/png", "image/jpeg", "image/webp"},
    ),
    "video": (
        {".mp4", ".webm", ".mov", ".mkv"},
        {"video/mp4", "video/webm", "video/quicktime", "video/x-matroska"},
    ),
    "audio": (
        {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac", ".webm"},
        {
            "audio/mpeg",
            "audio/wav",
            "audio/x-wav",
            "audio/ogg",
            "audio/mp4",
            "audio/aac",
            "audio/flac",
            "audio/webm",
        },
    ),
}


@dataclass(frozen=True, slots=True)
class StoredAnimeMedia:
    storage_key: str
    file_name: str
    size_bytes: int
    checksum_sha256: str
    mime_type: str


class InvalidAnimeMediaError(ValueError):
    pass


class AnimeMediaStorage:
    def __init__(self, root: str | Path, max_size_bytes: int) -> None:
        self.root = Path(root).resolve()
        self.max_size_bytes = max_size_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, storage_key: str) -> Path:
        candidate = (self.root / storage_key).resolve()
        if self.root not in candidate.parents:
            raise InvalidAnimeMediaError("Chave de armazenamento inválida")
        return candidate

    @staticmethod
    def _validate_signature(path: Path, suffix: str) -> None:
        signature = path.read_bytes()[:16]
        valid = True
        if suffix == ".png":
            valid = signature.startswith(b"\x89PNG\r\n\x1a\n")
        elif suffix in {".jpg", ".jpeg"}:
            valid = signature.startswith(b"\xff\xd8\xff")
        elif suffix == ".webp":
            valid = signature.startswith(b"RIFF") and signature[8:12] == b"WEBP"
        elif suffix in {".mp4", ".mov", ".m4a"}:
            valid = len(signature) >= 12 and signature[4:8] == b"ftyp"
        elif suffix in {".webm", ".mkv"}:
            valid = signature.startswith(b"\x1aE\xdf\xa3")
        elif suffix == ".wav":
            valid = signature.startswith(b"RIFF") and signature[8:12] == b"WAVE"
        elif suffix == ".ogg":
            valid = signature.startswith(b"OggS")
        elif suffix == ".flac":
            valid = signature.startswith(b"fLaC")
        elif suffix == ".mp3":
            valid = signature.startswith(b"ID3") or (
                len(signature) >= 2 and signature[0] == 0xFF and signature[1] & 0xE0 == 0xE0
            )
        if not valid:
            raise InvalidAnimeMediaError("A assinatura do arquivo não corresponde à extensão")

    async def save(
        self, upload: UploadFile, organization_id: UUID, media_kind: str
    ) -> StoredAnimeMedia:
        if media_kind not in MEDIA_TYPES:
            raise InvalidAnimeMediaError("Tipo de mídia inválido")
        extensions, mime_types = MEDIA_TYPES[media_kind]
        file_name = (upload.filename or "").strip()
        suffix = Path(file_name).suffix.lower()
        if suffix not in extensions:
            raise InvalidAnimeMediaError(
                f"Extensão não permitida para {media_kind}: {suffix or 'ausente'}"
            )
        content_type = (upload.content_type or "application/octet-stream").lower()
        if content_type not in mime_types:
            raise InvalidAnimeMediaError(f"Tipo MIME não permitido: {content_type}")

        storage_key = f"{organization_id}/anime/{uuid4()}{suffix}"
        destination = self.resolve(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        size = 0
        try:
            with destination.open("wb") as target:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.max_size_bytes:
                        raise InvalidAnimeMediaError(
                            f"O arquivo excede {self.max_size_bytes // (1024 * 1024)} MB"
                        )
                    digest.update(chunk)
                    target.write(chunk)
            if size == 0:
                raise InvalidAnimeMediaError("O arquivo enviado está vazio")
            self._validate_signature(destination, suffix)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()
        return StoredAnimeMedia(
            storage_key=storage_key,
            file_name=file_name,
            size_bytes=size,
            checksum_sha256=digest.hexdigest(),
            mime_type=content_type,
        )

    def save_render(
        self, source: Path, organization_id: UUID, *, file_name: str
    ) -> StoredAnimeMedia:
        if not source.is_file() or source.stat().st_size == 0:
            raise InvalidAnimeMediaError("Renderização não gerou um arquivo válido")
        storage_key = f"{organization_id}/anime/renders/{uuid4()}.mp4"
        destination = self.resolve(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source, destination)
        digest = hashlib.sha256()
        with destination.open("rb") as rendered:
            while chunk := rendered.read(1024 * 1024):
                digest.update(chunk)
        return StoredAnimeMedia(
            storage_key=storage_key,
            file_name=file_name,
            size_bytes=destination.stat().st_size,
            checksum_sha256=digest.hexdigest(),
            mime_type="video/mp4",
        )

    def save_generated(
        self,
        source: Path,
        organization_id: UUID,
        *,
        media_kind: str,
        file_name: str,
        mime_type: str,
    ) -> StoredAnimeMedia:
        if media_kind not in MEDIA_TYPES:
            raise InvalidAnimeMediaError("Tipo de midia gerada invalido")
        suffix = Path(file_name).suffix.lower()
        extensions, mime_types = MEDIA_TYPES[media_kind]
        if suffix not in extensions or mime_type not in mime_types:
            raise InvalidAnimeMediaError("Formato de midia gerada invalido")
        if not source.is_file() or source.stat().st_size == 0:
            raise InvalidAnimeMediaError("O provedor nao gerou um arquivo valido")
        storage_key = f"{organization_id}/anime/generated/{uuid4()}{suffix}"
        destination = self.resolve(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source, destination)
        try:
            self._validate_signature(destination, suffix)
            digest = hashlib.sha256()
            with destination.open("rb") as generated:
                while chunk := generated.read(1024 * 1024):
                    digest.update(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        return StoredAnimeMedia(
            storage_key=storage_key,
            file_name=file_name,
            size_bytes=destination.stat().st_size,
            checksum_sha256=digest.hexdigest(),
            mime_type=mime_type,
        )

    def delete(self, storage_key: str) -> None:
        self.resolve(storage_key).unlink(missing_ok=True)
