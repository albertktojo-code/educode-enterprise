from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
READER = PROJECT_ROOT / "frontend/src/features/comicReaderAccess"


def test_reader_exposes_zoom_orientation_and_continuous_reading() -> None:
    toolbar = (READER / "AccessibilityToolbar.tsx").read_text(encoding="utf-8")
    surface = (READER / "ReaderSurface.tsx").read_text(encoding="utf-8")

    assert 'aria-label="Nível de zoom"' in toolbar
    assert 'value="PORTRAIT"' in toolbar
    assert 'value="LANDSCAPE"' in toolbar
    assert 'mode === "VERTICAL"' in surface


def test_reader_exposes_screen_reader_audio_description_and_narration() -> None:
    toolbar = (READER / "AccessibilityToolbar.tsx").read_text(encoding="utf-8")
    surface = (READER / "ReaderSurface.tsx").read_text(encoding="utf-8")
    page = (READER / "ComicReaderPage.tsx").read_text(encoding="utf-8")

    assert "Modo leitor de tela" in toolbar
    assert "Narrar ao avançar" in toolbar
    assert "panel.audio_description" in surface
    assert 'aria-live={preferences.screen_reader_mode ? "polite" : "off"}' in surface
    assert "preferences.auto_play_narration" in page
    assert "SpeechSynthesisUtterance" in page


def test_reader_preferences_remain_in_canonical_json_store() -> None:
    api = (READER / "api.ts").read_text(encoding="utf-8")
    policies = (
        PROJECT_ROOT / "backend/app/comic_reader_access/policies.py"
    ).read_text(encoding="utf-8")

    assert "preferences/me" in api
    assert '"zoom_level": 1.0' in policies
    assert '"orientation": "AUTO"' in policies
