from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.actor_context import ActorContext, get_project_session, resolve_actor_context
from app.models.delivery import AttemptStatus, MaterialAssignment, StudentAttempt
from app.services.consolidated_audit import append_domain_audit

from .models import StudentPortfolioEntry
from .schemas import PortfolioEntryCreate, PortfolioEntryRead, PortfolioEntryUpdate

router = APIRouter(prefix="/student/portfolio", tags=["student-portfolio"])
SessionDep = Annotated[AsyncSession, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]


def require_student(actor: ActorContext) -> None:
    if not actor.is_superuser and not actor.has_any_role("STUDENT", "LEARNER", "MEMBER"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Área exclusiva do estudante.")


async def own_entry_or_404(
    session: AsyncSession, actor: ActorContext, entry_id: UUID
) -> StudentPortfolioEntry:
    entry = await session.scalar(
        select(StudentPortfolioEntry).where(
            StudentPortfolioEntry.id == entry_id,
            StudentPortfolioEntry.organization_id == actor.organization_id,
            StudentPortfolioEntry.student_user_id == actor.user_id,
        )
    )
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidência do portfólio não encontrada.")
    return entry


@router.get("/entries", response_model=list[PortfolioEntryRead])
async def list_entries(session: SessionDep, actor: ActorDep) -> list[StudentPortfolioEntry]:
    require_student(actor)
    entries = await session.scalars(
        select(StudentPortfolioEntry)
        .where(
            StudentPortfolioEntry.organization_id == actor.organization_id,
            StudentPortfolioEntry.student_user_id == actor.user_id,
        )
        .order_by(StudentPortfolioEntry.created_at.desc())
    )
    return list(entries.all())


@router.post("/entries", response_model=PortfolioEntryRead, status_code=status.HTTP_201_CREATED)
async def create_entry(
    data: PortfolioEntryCreate, session: SessionDep, actor: ActorDep
) -> StudentPortfolioEntry:
    require_student(actor)
    existing = await session.scalar(
        select(StudentPortfolioEntry).where(
            StudentPortfolioEntry.organization_id == actor.organization_id,
            StudentPortfolioEntry.student_user_id == actor.user_id,
            StudentPortfolioEntry.assignment_id == data.assignment_id,
        )
    )
    if existing is not None:
        return existing

    attempt = await session.scalar(
        select(StudentAttempt)
        .join(MaterialAssignment, MaterialAssignment.id == StudentAttempt.assignment_id)
        .where(
            StudentAttempt.organization_id == actor.organization_id,
            StudentAttempt.student_id == actor.user_id,
            StudentAttempt.assignment_id == data.assignment_id,
            StudentAttempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.GRADED]),
            MaterialAssignment.organization_id == actor.organization_id,
        )
        .order_by(StudentAttempt.percentage.desc(), StudentAttempt.submitted_at.desc().nullslast())
    )
    if attempt is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Somente uma atividade concluída pelo estudante pode virar evidência.",
        )
    assignment = await session.get(MaterialAssignment, data.assignment_id)
    if assignment is None or assignment.organization_id != actor.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Atividade não encontrada.")

    entry = StudentPortfolioEntry(
        organization_id=actor.organization_id,
        student_user_id=actor.user_id,
        assignment_id=assignment.id,
        attempt_id=attempt.id,
        title_snapshot=assignment.title,
        assignment_type_snapshot=assignment.assignment_type.value,
        percentage_snapshot=attempt.percentage,
        completed_at_snapshot=attempt.graded_at or attempt.submitted_at,
        reflection=data.reflection.strip(),
    )
    session.add(entry)
    await session.flush()
    await append_domain_audit(
        session,
        actor=actor,
        module_name="student_portfolio",
        action="portfolio.evidence.curated",
        entity_type="student_portfolio_entry",
        entity_id=entry.id,
        details={"assignment_id": str(assignment.id), "attempt_id": str(attempt.id)},
    )
    await session.commit()
    await session.refresh(entry)
    return entry


@router.patch("/entries/{entry_id}", response_model=PortfolioEntryRead)
async def update_entry(
    entry_id: UUID, data: PortfolioEntryUpdate, session: SessionDep, actor: ActorDep
) -> StudentPortfolioEntry:
    require_student(actor)
    entry = await own_entry_or_404(session, actor, entry_id)
    entry.reflection = data.reflection.strip()
    entry.revision += 1
    await append_domain_audit(
        session,
        actor=actor,
        module_name="student_portfolio",
        action="portfolio.reflection.updated",
        entity_type="student_portfolio_entry",
        entity_id=entry.id,
        details={"revision": entry.revision, "reflection_length": len(entry.reflection)},
    )
    await session.commit()
    await session.refresh(entry)
    return entry


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(entry_id: UUID, session: SessionDep, actor: ActorDep) -> Response:
    require_student(actor)
    entry = await own_entry_or_404(session, actor, entry_id)
    await append_domain_audit(
        session,
        actor=actor,
        module_name="student_portfolio",
        action="portfolio.evidence.removed",
        entity_type="student_portfolio_entry",
        entity_id=entry.id,
        details={"assignment_id": str(entry.assignment_id)},
    )
    await session.delete(entry)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
