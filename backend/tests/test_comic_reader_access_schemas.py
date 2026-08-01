import uuid

import pytest
from pydantic import ValidationError

from app.comic_reader_access.schemas import NarrationTrackCreate, ReaderPreferenceUpsert


def test_reader_mode_is_normalized():
    item = ReaderPreferenceUpsert(reader_mode="vertical")
    assert item.reader_mode == "VERTICAL"


def test_invalid_reader_mode_is_rejected():
    with pytest.raises(ValidationError):
        ReaderPreferenceUpsert(reader_mode="cinema")


def test_recorded_narration_requires_audio():
    with pytest.raises(ValidationError):
        NarrationTrackCreate(source_type="HUMAN_RECORDING", transcript="Texto")


def test_recorded_narration_accepts_asset():
    item = NarrationTrackCreate(
        source_type="UPLOADED_AUDIO",
        transcript="Texto",
        audio_asset_id=uuid.uuid4(),
    )
    assert item.source_type == "UPLOADED_AUDIO"
