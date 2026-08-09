from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.education import Classroom
from app.school_admissions.models import (
    EnrollmentContract,
    EnrollmentContractAcceptance,
    EnrollmentContractTemplate,
    EnrollmentContractVersion,
    GuardianProfile,
    SchoolUnit,
    StudentEnrollmentApplication,
    StudentGuardianLink,
    StudentProfile,
)
from app.school_admissions.schemas import (
    EnrollmentContractAcceptanceRead,
    EnrollmentContractRead,
    EnrollmentContractVersionRead,
)

PLACEHOLDER = re.compile(r"{{\s*([a-z_][a-z0-9_]*)\s*}}")
CANONICAL_VARIABLES = {
    "nome_aluno",
    "nome_responsavel",
    "ano_letivo",
    "serie",
    "turma",
    "turno",
    "unidade_escolar",
    "data_geracao",
}


def validate_template(body: str) -> set[str]:
    variables = set(PLACEHOLDER.findall(body))
    unknown = variables - CANONICAL_VARIABLES
    if unknown:
        raise HTTPException(
            status_code=422, detail=f"Variáveis não permitidas: {', '.join(sorted(unknown))}"
        )
    if not variables:
        raise HTTPException(
            status_code=422, detail="O template precisa conter ao menos uma variável"
        )
    return variables


def render_contract(body: str, variables: dict[str, str]) -> tuple[str, str]:
    validate_template(body)
    rendered = PLACEHOLDER.sub(lambda match: variables.get(match.group(1), ""), body)
    return rendered, hashlib.sha256(rendered.encode("utf-8")).hexdigest()


async def contract_variables(
    session: AsyncSession,
    application: StudentEnrollmentApplication,
    guardian_id: UUID,
) -> tuple[GuardianProfile, dict[str, str]]:
    guardian = await session.scalar(
        select(GuardianProfile)
        .join(StudentGuardianLink, StudentGuardianLink.guardian_profile_id == GuardianProfile.id)
        .where(
            GuardianProfile.id == guardian_id,
            GuardianProfile.organization_id == application.organization_id,
            StudentGuardianLink.organization_id == application.organization_id,
            StudentGuardianLink.student_profile_id == application.student_profile_id,
        )
    )
    if guardian is None:
        raise HTTPException(status_code=404, detail="Responsável vinculado não encontrado")
    student = await session.scalar(
        select(StudentProfile).where(StudentProfile.id == application.student_profile_id)
    )
    classroom = await session.scalar(
        select(Classroom).where(Classroom.id == application.classroom_id)
    )
    unit = await session.scalar(
        select(SchoolUnit).where(SchoolUnit.id == application.school_unit_id)
    )
    if student is None or classroom is None or unit is None:
        raise HTTPException(
            status_code=409, detail="Dados da matrícula incompletos para o contrato"
        )
    return guardian, {
        "nome_aluno": student.social_name or student.legal_name,
        "nome_responsavel": guardian.full_name,
        "ano_letivo": str(application.academic_year),
        "serie": application.intended_grade,
        "turma": classroom.name,
        "turno": application.intended_shift,
        "unidade_escolar": unit.name,
        "data_geracao": datetime.now(UTC).date().isoformat(),
    }


async def contract_or_404(
    session: AsyncSession, organization_id: UUID, contract_id: UUID, *, lock: bool = False
) -> EnrollmentContract:
    statement = select(EnrollmentContract).where(
        EnrollmentContract.id == contract_id,
        EnrollmentContract.organization_id == organization_id,
    )
    if lock:
        statement = statement.with_for_update()
    contract = await session.scalar(statement)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contrato de matrícula não encontrado")
    return contract


async def contract_read(
    session: AsyncSession, contract: EnrollmentContract
) -> EnrollmentContractRead:
    template = await session.scalar(
        select(EnrollmentContractTemplate).where(
            EnrollmentContractTemplate.id == contract.template_id
        )
    )
    versions = list(
        (
            await session.scalars(
                select(EnrollmentContractVersion)
                .where(
                    EnrollmentContractVersion.organization_id == contract.organization_id,
                    EnrollmentContractVersion.contract_id == contract.id,
                )
                .order_by(EnrollmentContractVersion.version_number.desc())
            )
        ).all()
    )
    acceptance = await session.scalar(
        select(EnrollmentContractAcceptance).where(
            EnrollmentContractAcceptance.organization_id == contract.organization_id,
            EnrollmentContractAcceptance.contract_id == contract.id,
        )
    )
    guardian = None
    if acceptance:
        guardian = await session.scalar(
            select(GuardianProfile).where(GuardianProfile.id == acceptance.guardian_profile_id)
        )
    elif versions:
        guardian_id = versions[0].variables_snapshot.get("guardian_profile_id")
        if guardian_id:
            guardian = await session.scalar(
                select(GuardianProfile).where(GuardianProfile.id == UUID(guardian_id))
            )
    return EnrollmentContractRead(
        id=contract.id,
        application_id=contract.application_id,
        template_id=contract.template_id,
        template_name=template.name if template else "Template indisponível",
        guardian_profile_id=guardian.id if guardian else None,
        guardian_name=guardian.full_name if guardian else None,
        status=contract.status,
        current_version_number=contract.current_version_number,
        void_reason=contract.void_reason,
        versions=[
            EnrollmentContractVersionRead.model_validate(item, from_attributes=True)
            for item in versions
        ],
        acceptance=(
            EnrollmentContractAcceptanceRead.model_validate(acceptance, from_attributes=True)
            if acceptance
            else None
        ),
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )
