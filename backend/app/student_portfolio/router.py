from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from secrets import token_hex
from typing import Annotated
from urllib.parse import urlsplit
from uuid import UUID

import qrcode
import qrcode.image.svg
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.anime_studio.models import AnimeProject
from app.api.actor_context import ActorContext, get_project_session, resolve_actor_context
from app.models.auth import Membership, Organization, OrganizationRole, User
from app.models.comic import GeneratedComic
from app.models.delivery import AttemptStatus, MaterialAssignment, StudentAttempt, UserNotification
from app.models.education import Project
from app.services.consolidated_audit import append_domain_audit

from .models import StudentCertificate, StudentPortfolioEntry
from .schemas import (
    CertificateIssue,
    CertificateRead,
    CertificateRevoke,
    CertificateStudentRead,
    PortfolioEntryCreate,
    PortfolioEntryRead,
    PortfolioEntryUpdate,
    PortfolioProductionRead,
    PublicCertificateEvidence,
    PublicCertificateRead,
)

router = APIRouter(prefix="/student/portfolio", tags=["student-portfolio"])
SessionDep = Annotated[AsyncSession, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]


def require_student(actor: ActorContext) -> None:
    if not actor.is_superuser and not actor.has_any_role("STUDENT", "LEARNER", "MEMBER"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Área exclusiva do estudante.")


def require_educator(actor: ActorContext) -> None:
    if not actor.is_superuser and not actor.has_any_role("TEACHER", "ADMIN", "OWNER"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Emissão exclusiva de educadores.")


@router.get(
    "/certificates/verify/{verification_code}",
    response_model=PublicCertificateRead,
)
async def verify_certificate(
    verification_code: str, session: SessionDep
) -> PublicCertificateRead:
    student = aliased(User)
    issuer = aliased(User)
    row = (
        await session.execute(
            select(
                StudentCertificate,
                student.full_name,
                issuer.full_name,
                Organization.name,
            )
            .join(student, student.id == StudentCertificate.student_user_id)
            .join(issuer, issuer.id == StudentCertificate.issued_by_user_id)
            .join(Organization, Organization.id == StudentCertificate.organization_id)
            .where(
                StudentCertificate.verification_code
                == verification_code.strip().upper()
            )
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Certificado não encontrado.")

    certificate, student_name, issuer_name, organization_name = row
    try:
        evidence_ids = [UUID(item) for item in certificate.evidence_entry_ids]
    except ValueError:
        evidence_ids = []
    entries = list(
        (
            await session.scalars(
                select(StudentPortfolioEntry).where(
                    StudentPortfolioEntry.organization_id
                    == certificate.organization_id,
                    StudentPortfolioEntry.student_user_id
                    == certificate.student_user_id,
                    StudentPortfolioEntry.id.in_(evidence_ids),
                )
            )
        ).all()
    )
    entries_by_id = {item.id: item for item in entries}
    public_evidence = [
        PublicCertificateEvidence(
            title=entry.title_snapshot,
            assignment_type=entry.assignment_type_snapshot,
            percentage=entry.percentage_snapshot,
        )
        for entry_id in evidence_ids
        if (entry := entries_by_id.get(entry_id)) is not None
    ]
    return PublicCertificateRead(
        title=certificate.title,
        description=certificate.description,
        verification_code=certificate.verification_code,
        status=certificate.status,
        issued_at=certificate.issued_at,
        revoked_at=certificate.revoked_at,
        revocation_reason=certificate.revocation_reason,
        student_name=student_name,
        issuer_name=issuer_name,
        organization_name=organization_name,
        evidence=public_evidence,
    )


@router.get("/certificates/verify/{verification_code}/qr")
async def certificate_qr_code(
    verification_code: str,
    session: SessionDep,
    origin: str = Query(min_length=8, max_length=300),
) -> Response:
    normalized_code = verification_code.strip().upper()
    certificate_id = await session.scalar(
        select(StudentCertificate.id).where(
            StudentCertificate.verification_code == normalized_code
        )
    )
    if certificate_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Certificado não encontrado.")
    parsed_origin = urlsplit(origin)
    if (
        parsed_origin.scheme not in {"http", "https"}
        or not parsed_origin.netloc
        or parsed_origin.username
        or parsed_origin.password
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Origem inválida.")
    public_url = (
        f"{parsed_origin.scheme}://{parsed_origin.netloc}"
        f"/credentials/verificar/{normalized_code}"
    )
    image = qrcode.make(public_url, image_factory=qrcode.image.svg.SvgPathImage)
    output = BytesIO()
    image.save(output)
    return Response(
        content=output.getvalue(),
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/educator/students", response_model=list[CertificateStudentRead])
async def list_certificate_students(
    session: SessionDep, actor: ActorDep
) -> list[CertificateStudentRead]:
    require_educator(actor)
    rows = (
        await session.execute(
            select(User.id, User.full_name, User.email)
            .join(Membership, Membership.user_id == User.id)
            .where(
                Membership.organization_id == actor.organization_id,
                Membership.role == OrganizationRole.MEMBER,
                Membership.is_active.is_(True),
                User.is_active.is_(True),
            )
            .order_by(User.full_name, User.email)
        )
    ).all()
    return [
        CertificateStudentRead(id=user_id, full_name=full_name, email=email)
        for user_id, full_name, email in rows
    ]


@router.get(
    "/educator/students/{student_user_id}/entries",
    response_model=list[PortfolioEntryRead],
)
async def list_student_evidence(
    student_user_id: UUID, session: SessionDep, actor: ActorDep
) -> list[StudentPortfolioEntry]:
    require_educator(actor)
    entries = await session.scalars(
        select(StudentPortfolioEntry)
        .where(
            StudentPortfolioEntry.organization_id == actor.organization_id,
            StudentPortfolioEntry.student_user_id == student_user_id,
        )
        .order_by(StudentPortfolioEntry.created_at.desc())
    )
    return list(entries.all())


@router.get(
    "/educator/students/{student_user_id}/certificates",
    response_model=list[CertificateRead],
)
async def list_student_certificates(
    student_user_id: UUID, session: SessionDep, actor: ActorDep
) -> list[StudentCertificate]:
    require_educator(actor)
    rows = await session.scalars(
        select(StudentCertificate)
        .where(
            StudentCertificate.organization_id == actor.organization_id,
            StudentCertificate.student_user_id == student_user_id,
        )
        .order_by(StudentCertificate.issued_at.desc())
    )
    return list(rows.all())


@router.get("/certificates", response_model=list[CertificateRead])
async def list_certificates(session: SessionDep, actor: ActorDep) -> list[StudentCertificate]:
    require_student(actor)
    rows = await session.scalars(
        select(StudentCertificate)
        .where(
            StudentCertificate.organization_id == actor.organization_id,
            StudentCertificate.student_user_id == actor.user_id,
        )
        .order_by(StudentCertificate.issued_at.desc())
    )
    return list(rows.all())


@router.post("/certificates", response_model=CertificateRead, status_code=201)
async def issue_certificate(
    data: CertificateIssue, session: SessionDep, actor: ActorDep
) -> StudentCertificate:
    require_educator(actor)
    entries = list(
        (
            await session.scalars(
                select(StudentPortfolioEntry).where(
                    StudentPortfolioEntry.organization_id == actor.organization_id,
                    StudentPortfolioEntry.student_user_id == data.student_user_id,
                    StudentPortfolioEntry.id.in_(data.evidence_entry_ids),
                )
            )
        ).all()
    )
    if len(entries) != len(set(data.evidence_entry_ids)):
        raise HTTPException(
            422, "Todas as evidências devem pertencer ao estudante e à organização."
        )
    certificate = StudentCertificate(
        organization_id=actor.organization_id,
        student_user_id=data.student_user_id,
        issued_by_user_id=actor.user_id,
        title=data.title.strip(),
        description=data.description.strip(),
        verification_code=token_hex(12).upper(),
        evidence_entry_ids=[str(item.id) for item in entries],
    )
    session.add(certificate)
    session.add(
        UserNotification(
            organization_id=actor.organization_id,
            user_id=data.student_user_id,
            notification_type="certificate_issued",
            title="Novo certificado emitido",
            message=f"{certificate.title} foi adicionado ao seu portfólio.",
            action_path="/aluno/portfolio",
        )
    )
    await session.flush()
    await append_domain_audit(
        session,
        actor=actor,
        module_name="student_portfolio",
        action="certificate.issued",
        entity_type="student_certificate",
        entity_id=certificate.id,
        details={"student_user_id": str(data.student_user_id), "evidence_count": len(entries)},
    )
    await session.commit()
    await session.refresh(certificate)
    return certificate


@router.post("/certificates/{certificate_id}/revoke", response_model=CertificateRead)
async def revoke_certificate(
    certificate_id: UUID, data: CertificateRevoke, session: SessionDep, actor: ActorDep
) -> StudentCertificate:
    require_educator(actor)
    certificate = await session.scalar(
        select(StudentCertificate).where(
            StudentCertificate.id == certificate_id,
            StudentCertificate.organization_id == actor.organization_id,
        )
    )
    if certificate is None:
        raise HTTPException(404, "Certificado não encontrado.")
    if certificate.status != "revoked":
        certificate.status = "revoked"
        certificate.revoked_at = datetime.now(UTC)
        certificate.revoked_by_user_id = actor.user_id
        certificate.revocation_reason = data.reason.strip()
        session.add(
            UserNotification(
                organization_id=actor.organization_id,
                user_id=certificate.student_user_id,
                notification_type="certificate_revoked",
                title="Certificado revogado",
                message=(
                    f"{certificate.title} foi revogado. "
                    f"Motivo: {certificate.revocation_reason}"
                ),
                action_path="/aluno/portfolio",
            )
        )
        await append_domain_audit(
            session,
            actor=actor,
            module_name="student_portfolio",
            action="certificate.revoked",
            entity_type="student_certificate",
            entity_id=certificate.id,
            details={"reason": certificate.revocation_reason},
        )
        await session.commit()
        await session.refresh(certificate)
    return certificate


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


@router.get("/productions", response_model=list[PortfolioProductionRead])
async def list_authored_productions(
    session: SessionDep, actor: ActorDep
) -> list[PortfolioProductionRead]:
    require_student(actor)
    projects = list(
        (
            await session.scalars(
                select(Project).where(
                    Project.organization_id == actor.organization_id,
                    Project.owner_id == actor.user_id,
                )
            )
        ).all()
    )
    comics = list(
        (
            await session.scalars(
                select(GeneratedComic).where(
                    GeneratedComic.organization_id == actor.organization_id,
                    GeneratedComic.created_by_user_id == actor.user_id,
                )
            )
        ).all()
    )
    animes = list(
        (
            await session.scalars(
                select(AnimeProject).where(
                    AnimeProject.organization_id == actor.organization_id,
                    AnimeProject.created_by_user_id == actor.user_id,
                )
            )
        ).all()
    )
    productions = [
        PortfolioProductionRead(
            id=item.id,
            kind="project",
            title=item.title,
            description=item.description or "Projeto autoral",
            status=item.status.value,
            updated_at=item.updated_at,
            route=f"/projetos/{item.id}",
        )
        for item in projects
    ]
    productions.extend(
        PortfolioProductionRead(
            id=item.id,
            kind="comic",
            title=item.title,
            description=item.synopsis or "HQ autoral",
            status=item.publication_status,
            updated_at=item.updated_at,
            route=f"/hqs/{item.id}",
        )
        for item in comics
    )
    productions.extend(
        PortfolioProductionRead(
            id=item.id,
            kind="anime",
            title=item.title,
            description=item.synopsis or "Produção audiovisual autoral",
            status=item.status,
            updated_at=item.updated_at,
            route=f"/anime-studio/{item.id}",
        )
        for item in animes
    )
    return sorted(productions, key=lambda item: item.updated_at, reverse=True)


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
