from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
API = PROJECT_ROOT / "frontend/src/features/animeStudio/api.ts"
EDITOR = PROJECT_ROOT / "frontend/src/features/animeStudio/AnimeCheckpointEditor.tsx"
STUDIO = PROJECT_ROOT / "frontend/src/features/animeStudio/AnimeStudioPage.tsx"


def test_studio_reuses_canonical_assignment_catalog() -> None:
    api = API.read_text(encoding="utf-8")
    studio = STUDIO.read_text(encoding="utf-8")

    assert "api.get<AssignmentSummary[]>('/delivery/assignments')" in api
    assert "animeStudioApi.listAssignments().then(setAssignments)" in studio
    assert "'activities', 'Atividades'" in studio


def test_checkpoint_authoring_preserves_existing_production_notes() -> None:
    studio = STUDIO.read_text(encoding="utf-8")

    assert "...project.production_notes" in studio
    assert "interactive_checkpoints: checkpoints" in studio
    assert "AnimeCheckpointEditor" in studio


def test_editor_supports_preview_crud_and_accessibility() -> None:
    editor = EDITOR.read_text(encoding="utf-8")

    assert "assignment.status === 'scheduled'" in editor
    assert "assignment.status === 'published'" in editor
    assert "Navegar pela prévia" in editor
    assert "Pausar o vídeo neste instante" in editor
    assert "Marcar como etapa obrigatória" in editor
    assert "updateCheckpoint" in editor
    assert "removeCheckpoint" in editor
    assert 'to="/publicacoes"' in editor

