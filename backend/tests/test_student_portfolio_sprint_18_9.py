from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.actor_context import ActorContext
from app.student_portfolio.router import require_student
from app.student_portfolio.schemas import PortfolioEntryCreate, PortfolioEntryUpdate

BACKEND_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BACKEND_ROOT.parent
FRONTEND_ROOT = WORKSPACE_ROOT / "frontend"
if not FRONTEND_ROOT.exists():
    FRONTEND_ROOT = Path("/frontend")


def actor(*roles: str) -> ActorContext:
    return ActorContext(
        user_id=uuid4(),
        organization_id=uuid4(),
        membership_id=uuid4(),
        roles=frozenset(roles),
    )


def test_portfolio_accepts_only_student_actor() -> None:
    require_student(actor("STUDENT"))
    with pytest.raises(HTTPException) as denied:
        require_student(actor("TEACHER"))
    assert denied.value.status_code == 403


def test_reflection_contract_limits_content() -> None:
    assignment_id = uuid4()
    assert PortfolioEntryCreate(assignment_id=assignment_id).reflection == ""
    assert PortfolioEntryUpdate(reflection="O que aprendi").reflection == "O que aprendi"
    with pytest.raises(ValidationError):
        PortfolioEntryUpdate(reflection="x" * 2001)


def test_backend_scopes_entries_and_sources_to_owner_and_organization() -> None:
    router = (BACKEND_ROOT / "app/student_portfolio/router.py").read_text(encoding="utf-8")
    assert "StudentPortfolioEntry.organization_id == actor.organization_id" in router
    assert "StudentPortfolioEntry.student_user_id == actor.user_id" in router
    assert "StudentAttempt.organization_id == actor.organization_id" in router
    assert "StudentAttempt.student_id == actor.user_id" in router
    assert "AttemptStatus.SUBMITTED" in router and "AttemptStatus.GRADED" in router
    assert 'module_name="student_portfolio"' in router


def test_migration_has_single_parent_constraints_and_rollback() -> None:
    migration = (BACKEND_ROOT / "alembic/versions/0057_student_portfolio_entries.py").read_text(
        encoding="utf-8"
    )
    assert 'down_revision: str | None = "0056_anime_audiovisual"' in migration
    assert "uq_student_portfolio_assignment" in migration
    assert "ck_student_portfolio_reflection_length" in migration
    assert 'op.drop_table("student_portfolio_entries")' in migration


def test_frontend_exposes_curate_reflect_and_remove_actions() -> None:
    page = (FRONTEND_ROOT / "src/pages/StudentPortfolioPage.tsx").read_text(encoding="utf-8")
    assert "'/student/portfolio/entries'" in page
    assert "Adicionar ao portfólio" in page
    assert "Salvar reflexão" in page
    assert "Remover da curadoria" in page
    assert 'aria-live="polite"' in page


def test_smoke_test_tracks_current_credentials_migration_head() -> None:
    smoke = (WORKSPACE_ROOT / "scripts/smoke_test.py").read_text(encoding="utf-8")
    assert 'version.get("migration_revision") == "0062_enrollment_movements"' in smoke
