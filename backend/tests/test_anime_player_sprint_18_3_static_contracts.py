from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PLAYER = (
    PROJECT_ROOT
    / "frontend/src/features/animeStudio/AnimeStudentLibraryPage.tsx"
)


def test_player_supports_speed_and_adaptive_quality() -> None:
    player = PLAYER.read_text(encoding="utf-8")

    assert "playbackRate" in player
    assert 'value={0.75}' in player
    assert 'value={2}' in player
    assert "automaticRendition" in player
    assert "connection?.saveData" in player
    assert '<option value="auto">Automática</option>' in player


def test_player_restores_and_saves_progress_by_publication_revision() -> None:
    player = PLAYER.read_text(encoding="utf-8")

    assert "progressKey(projectId: string, revision: number)" in player
    assert "selected.publication.render_revision" in player
    assert "localStorage.getItem" in player
    assert "localStorage.setItem" in player
    assert "onLoadedMetadata" in player
    assert "onTimeUpdate" in player
    assert "onPause" in player


def test_transcript_is_navigable_and_audio_description_is_identified() -> None:
    player = PLAYER.read_text(encoding="utf-8")

    assert "seekTo(cue.start_ms)" in player
    assert "videoRef.current.currentTime" in player
    assert "Transcrição navegável" in player
    assert "cue.cue_kind === 'audio_description'" in player
    assert "Audiodescrição disponível" in player
