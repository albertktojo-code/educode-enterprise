from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class AnimeMediaUploadRead(BaseModel):
    asset_id: UUID
    file_id: UUID
    file_name: str
    media_kind: Literal["image", "video", "audio"]
    mime_type: str
    size_bytes: int
    download_path: str
