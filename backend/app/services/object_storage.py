from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Protocol

from app.core.config import Settings


@dataclass(frozen=True, slots=True)
class ObjectMetadata:
    key: str
    size_bytes: int
    checksum_sha256: str
    content_type: str


class ObjectStorageError(RuntimeError):
    pass


def normalize_object_key(value: str) -> str:
    key = value.strip().replace("\\", "/")
    key = re.sub(r"/+", "/", key).lstrip("/")
    parts = [part for part in key.split("/") if part not in {"", "."}]
    if not parts or any(part == ".." for part in parts):
        raise ObjectStorageError("Chave de objeto inválida")
    normalized = "/".join(parts)
    if len(normalized) > 1024:
        raise ObjectStorageError("Chave de objeto excede 1024 caracteres")
    return normalized


class ObjectStoragePort(Protocol):
    async def healthcheck(self) -> dict[str, object]: ...
    async def put_bytes(self, key: str, content: bytes, content_type: str) -> ObjectMetadata: ...
    async def get_bytes(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...


class LocalObjectStorage:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        normalized = normalize_object_key(key)
        candidate = (self.root / normalized).resolve()
        if self.root != candidate and self.root not in candidate.parents:
            raise ObjectStorageError("Chave de objeto fora do diretório permitido")
        return candidate

    async def healthcheck(self) -> dict[str, object]:
        started = perf_counter()
        marker = self.root / ".educode-healthcheck"
        try:
            marker.write_text("ok", encoding="utf-8")
            marker.unlink(missing_ok=True)
            return {
                "status": "healthy",
                "provider": "local",
                "latency_ms": round((perf_counter() - started) * 1000, 3),
                "root": str(self.root),
            }
        except OSError as exc:
            return {
                "status": "unavailable",
                "provider": "local",
                "latency_ms": round((perf_counter() - started) * 1000, 3),
                "error": str(exc),
            }

    async def put_bytes(self, key: str, content: bytes, content_type: str) -> ObjectMetadata:
        destination = self._resolve(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(destination.write_bytes, content)
        return ObjectMetadata(
            key=normalize_object_key(key),
            size_bytes=len(content),
            checksum_sha256=hashlib.sha256(content).hexdigest(),
            content_type=content_type,
        )

    async def get_bytes(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.exists():
            raise ObjectStorageError("Objeto não encontrado")
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._resolve(key).unlink, True)


class S3CompatibleObjectStorage:
    def __init__(
        self,
        *,
        endpoint_url: str,
        bucket_name: str,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        prefix: str = "educode",
        use_ssl: bool = True,
    ) -> None:
        if not bucket_name:
            raise ObjectStorageError("Bucket S3 não configurado")
        self.endpoint_url = endpoint_url or None
        self.bucket_name = bucket_name
        self.region = region
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.prefix = prefix.strip("/")
        self.use_ssl = use_ssl

    def _client(self):
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - validado no container final
            raise ObjectStorageError("Dependência boto3 não está instalada") from exc
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id=self.access_key_id or None,
            aws_secret_access_key=self.secret_access_key or None,
            use_ssl=self.use_ssl,
        )

    def _key(self, key: str) -> str:
        normalized = normalize_object_key(key)
        return f"{self.prefix}/{normalized}" if self.prefix else normalized

    async def healthcheck(self) -> dict[str, object]:
        started = perf_counter()
        try:
            client = self._client()
            await asyncio.to_thread(client.head_bucket, Bucket=self.bucket_name)
            return {
                "status": "healthy",
                "provider": "s3",
                "latency_ms": round((perf_counter() - started) * 1000, 3),
                "bucket": self.bucket_name,
                "endpoint": self.endpoint_url or "aws",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "unavailable",
                "provider": "s3",
                "latency_ms": round((perf_counter() - started) * 1000, 3),
                "bucket": self.bucket_name,
                "error": str(exc),
            }

    async def put_bytes(self, key: str, content: bytes, content_type: str) -> ObjectMetadata:
        client = self._client()
        object_key = self._key(key)
        checksum = hashlib.sha256(content).hexdigest()
        await asyncio.to_thread(
            client.put_object,
            Bucket=self.bucket_name,
            Key=object_key,
            Body=content,
            ContentType=content_type,
            Metadata={"sha256": checksum},
        )
        return ObjectMetadata(
            key=object_key,
            size_bytes=len(content),
            checksum_sha256=checksum,
            content_type=content_type,
        )

    async def get_bytes(self, key: str) -> bytes:
        client = self._client()
        response = await asyncio.to_thread(
            client.get_object,
            Bucket=self.bucket_name,
            Key=self._key(key),
        )
        return await asyncio.to_thread(response["Body"].read)

    async def delete(self, key: str) -> None:
        client = self._client()
        await asyncio.to_thread(
            client.delete_object,
            Bucket=self.bucket_name,
            Key=self._key(key),
        )


def storage_from_settings(settings: Settings) -> ObjectStoragePort:
    if settings.object_storage_provider == "s3":
        return S3CompatibleObjectStorage(
            endpoint_url=settings.s3_endpoint_url,
            bucket_name=settings.s3_bucket_name,
            region=settings.s3_region,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            prefix=settings.s3_prefix,
            use_ssl=settings.s3_use_ssl,
        )
    return LocalObjectStorage(settings.object_storage_local_path)
