from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = PROJECT_ROOT / "backend/app/anime_studio/schemas.py"
SERVICES = PROJECT_ROOT / "backend/app/anime_studio/services.py"
PLAYER = PROJECT_ROOT / "frontend/src/features/animeStudio/AnimeStudentLibraryPage.tsx"


def test_publication_snapshots_validated_interactive_checkpoints() -> None:
    schemas = SCHEMAS.read_text(encoding="utf-8")
    services = SERVICES.read_text(encoding="utf-8")

    assert "class AnimeInteractiveCheckpoint(BaseModel):" in schemas
    assert "timestamp_ms: int = Field(ge=0" in schemas
    assert "assignment_id: UUID" in schemas
    assert "interactive_checkpoints: list[AnimeInteractiveCheckpoint]" in schemas
    assert 'project.production_notes.get("interactive_checkpoints", [])' in services
    assert "interactive_checkpoints=interactive_checkpoints" in services


def test_checkpoint_assignments_use_the_canonical_assessment_domain() -> None:
    services = SERVICES.read_text(encoding="utf-8")

    assert "from app.models.delivery import AssignmentStatus, MaterialAssignment" in services
    assert "MaterialAssignment.organization_id == actor.organization_id" in services
    assert "AssignmentStatus.SCHEDULED" in services
    assert "AssignmentStatus.PUBLISHED" in services


def test_student_player_pauses_and_routes_to_the_canonical_assignment() -> None:
    player = PLAYER.read_text(encoding="utf-8")

    assert "shownCheckpointIds" in player
    assert "if (checkpoint.pause_playback) video.pause()" in player
    assert "/aluno/atividades/${checkpoint.assignment_id}" in player
    assert "activeCheckpoint.assignment_id" in player
    assert "Abrir atividade" in player
    assert "Continuar vídeo" in player
