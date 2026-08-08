from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
API = PROJECT_ROOT / "frontend/src/features/animeStudio/api.ts"
PLAYER = PROJECT_ROOT / "frontend/src/features/animeStudio/AnimeStudentLibraryPage.tsx"
ASSIGNMENT = PROJECT_ROOT / "frontend/src/pages/StudentAssignmentPage.tsx"


def test_player_uses_canonical_student_assignment_progress() -> None:
    api = API.read_text(encoding="utf-8")
    player = PLAYER.read_text(encoding="utf-8")

    assert "api.get<StudentAssignmentCard[]>('/student/assignments')" in api
    assert "assignmentProgressById" in player
    assert "progress_status === 'completed'" in player
    assert "refreshAssignmentProgress" in player
    assert "window.addEventListener('focus', refreshOnFocus)" in player


def test_required_checkpoint_blocks_only_fulfillable_pending_activity() -> None:
    player = PLAYER.read_text(encoding="utf-8")

    assert "activeCheckpointBlocked" in player
    assert "activeCheckpoint?.required" in player
    assert "activeAssignment && !activeAssignmentCompleted" in player
    assert "activeAssignmentUnavailable" in player
    assert 'disabled={activeCheckpointBlocked}' in player
    assert "A atividade não está disponível para sua conta; o vídeo foi liberado." in player


def test_assignment_return_is_internal_and_restores_exact_checkpoint() -> None:
    player = PLAYER.read_text(encoding="utf-8")
    assignment = ASSIGNMENT.read_text(encoding="utf-8")

    assert "returnTo=${encodeURIComponent(returnPath)}" in player
    assert "requestedCheckpoint.timestamp_ms / 1000" in player
    assert "parsed.origin !== base" in assignment
    assert "parsed.pathname !== '/anime-library'" in assignment
    assert "if (returnPath) navigate(returnPath, { replace: true })" in assignment
    assert "← Voltar ao vídeo" in assignment

