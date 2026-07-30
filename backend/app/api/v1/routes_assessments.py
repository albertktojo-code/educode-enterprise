from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db_session
from app.models.assessment import (
    Assessment,
    AssessmentAuditEvent,
    AssessmentConnector,
    AssessmentImportJob,
    AssessmentOutcomeEvidence,
    QuestionBankItem,
)
from app.models.auth import Membership, OrganizationRole, User
from app.models.delivery import AssignmentQuestion, MaterialAssignment, StudentAttempt
from app.schemas.assessment import (
    AiQuestionGenerationRequest,
    AssessmentCreate,
    AssessmentItemAdd,
    AssessmentPublishRequest,
    AssessmentRead,
    AssessmentReviewRequest,
    AuditEventRead,
    BankItemCreate,
    BankItemRead,
    ImportExecuteRequest,
    ImportJobCreate,
    ImportJobRead,
    OutcomeRead,
    QuestionAnnulmentRequest,
    RecalculateRequest,
    StatisticalDatasetFromAssessments,
)
from app.schemas.delivery import AssignmentTeacherRead
from app.schemas.statistics import DatasetRead
from app.services.assessment import (
    AssessmentError,
    add_item_to_assessment,
    annul_question,
    create_assessment,
    create_bank_item,
    create_import_job,
    create_version,
    execute_import,
    freeze_assessment_dataset,
    generate_ai_items,
    get_assessment,
    publish_assessment,
    recalculate_assignment,
    recalculate_attempt_evidence,
    review_assessment,
)
from app.services.delivery import get_assignment, load_attempt

router = APIRouter(prefix="/assessments", tags=["Núcleo de Avaliação Integrada"])

TEACHER_ROLES = (
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.TEACHER,
)
ADMIN_ROLES = (OrganizationRole.OWNER, OrganizationRole.ADMIN)


def org_id(membership: Membership) -> UUID:
    return membership.organization_id


def assessment_error(exc: AssessmentError) -> HTTPException:
    message = str(exc)
    status = 409 if any(token in message.casefold() for token in ("bloqueada", "aprovada", "publicação")) else 422
    return HTTPException(status_code=status, detail=message)


@router.get("", response_model=list[AssessmentRead])
async def list_assessments(
    status: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[Assessment]:
    statement = select(Assessment).where(Assessment.organization_id == org_id(membership))
    if status:
        statement = statement.where(Assessment.status == status)
    if source_type:
        statement = statement.where(Assessment.source_type == source_type)
    result = await session.scalars(statement.order_by(Assessment.updated_at.desc()))
    rows: list[Assessment] = []
    for assessment in result.all():
        hydrated = await get_assessment(session, org_id(membership), assessment.id)
        if hydrated:
            rows.append(hydrated)
    return rows


@router.post("", response_model=AssessmentRead, status_code=201)
async def create_integrated_assessment(
    data: AssessmentCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> Assessment:
    try:
        assessment = await create_assessment(
            session,
            organization_id=org_id(membership),
            user_id=user.id,
            data=data,
        )
    except AssessmentError as exc:
        raise assessment_error(exc) from exc
    await session.commit()
    return await get_assessment(session, org_id(membership), assessment.id) or assessment


@router.get("/records/{assessment_id}", response_model=AssessmentRead)
async def read_assessment(
    assessment_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> Assessment:
    assessment = await get_assessment(session, org_id(membership), assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")
    return assessment


@router.post("/records/{assessment_id}/items", response_model=AssessmentRead, status_code=201)
async def attach_item(
    assessment_id: UUID,
    data: AssessmentItemAdd,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> Assessment:
    try:
        assessment = await add_item_to_assessment(
            session,
            organization_id=org_id(membership),
            user_id=user.id,
            assessment_id=assessment_id,
            item_id=data.item_id,
            position=data.position,
            points_override=data.points_override,
        )
    except AssessmentError as exc:
        raise assessment_error(exc) from exc
    await session.commit()
    return assessment


@router.post("/records/{assessment_id}/versions", response_model=AssessmentRead, status_code=201)
async def version_assessment(
    assessment_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> Assessment:
    try:
        assessment = await create_version(
            session,
            organization_id=org_id(membership),
            user_id=user.id,
            assessment_id=assessment_id,
        )
    except AssessmentError as exc:
        raise assessment_error(exc) from exc
    await session.commit()
    return assessment


@router.post("/records/{assessment_id}/review", response_model=AssessmentRead)
async def assessment_review(
    assessment_id: UUID,
    data: AssessmentReviewRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> Assessment:
    if data.decision == "approve" and membership.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Somente administradores podem aprovar avaliações")
    try:
        assessment = await review_assessment(
            session,
            organization_id=org_id(membership),
            user_id=user.id,
            assessment_id=assessment_id,
            decision=data.decision,
            notes=data.notes,
        )
    except AssessmentError as exc:
        raise assessment_error(exc) from exc
    await session.commit()
    return assessment


@router.post("/records/{assessment_id}/publish", response_model=AssignmentTeacherRead, status_code=201)
async def assessment_publish(
    assessment_id: UUID,
    data: AssessmentPublishRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> MaterialAssignment:
    try:
        assignment = await publish_assessment(
            session,
            organization_id=org_id(membership),
            user_id=user.id,
            user_name=user.full_name,
            assessment_id=assessment_id,
            data=data,
        )
    except (AssessmentError, ValueError) as exc:
        raise assessment_error(AssessmentError(str(exc))) from exc
    await session.commit()
    hydrated = await get_assignment(session, org_id(membership), assignment.id)
    return hydrated or assignment


@router.get("/question-bank/items", response_model=list[BankItemRead])
async def list_question_bank(
    source_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    skill_code: str | None = Query(default=None),
    ct_pillar: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[QuestionBankItem]:
    statement = select(QuestionBankItem).where(QuestionBankItem.organization_id == org_id(membership))
    if source_type:
        statement = statement.where(QuestionBankItem.source_type == source_type)
    if status:
        statement = statement.where(QuestionBankItem.status == status)
    result = list((await session.scalars(statement.order_by(QuestionBankItem.updated_at.desc()))).all())
    if skill_code:
        result = [item for item in result if skill_code in item.curriculum_skill_codes]
    if ct_pillar:
        result = [item for item in result if ct_pillar in item.ct_pillar_codes]
    return result


@router.post("/question-bank/items", response_model=BankItemRead, status_code=201)
async def create_question_bank_item(
    data: BankItemCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> QuestionBankItem:
    item = await create_bank_item(
        session,
        organization_id=org_id(membership),
        user_id=user.id,
        data=data,
    )
    await session.commit()
    await session.refresh(item)
    return item


@router.post("/ai/generate-items", response_model=list[BankItemRead], status_code=201)
async def generate_assessment_items(
    data: AiQuestionGenerationRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> list[QuestionBankItem]:
    try:
        items = await generate_ai_items(
            session,
            organization_id=org_id(membership),
            user_id=user.id,
            data=data,
        )
    except AssessmentError as exc:
        raise assessment_error(exc) from exc
    await session.commit()
    return items


@router.post("/imports", response_model=ImportJobRead, status_code=201)
async def create_assessment_import(
    data: ImportJobCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> AssessmentImportJob:
    job = await create_import_job(
        session,
        organization_id=org_id(membership),
        user_id=user.id,
        data=data,
    )
    await session.commit()
    await session.refresh(job)
    return job


@router.get("/imports/jobs", response_model=list[ImportJobRead])
async def list_import_jobs(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[AssessmentImportJob]:
    return list(
        (
            await session.scalars(
                select(AssessmentImportJob)
                .where(AssessmentImportJob.organization_id == org_id(membership))
                .order_by(AssessmentImportJob.created_at.desc())
            )
        ).all()
    )


@router.post("/imports/{job_id}/execute", response_model=AssessmentRead, status_code=201)
async def run_assessment_import(
    job_id: UUID,
    data: ImportExecuteRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> Assessment:
    job = await session.scalar(
        select(AssessmentImportJob).where(
            AssessmentImportJob.id == job_id,
            AssessmentImportJob.organization_id == org_id(membership),
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    try:
        assessment = await execute_import(
            session,
            organization_id=org_id(membership),
            user_id=user.id,
            job=job,
            data=data,
        )
    except AssessmentError as exc:
        raise assessment_error(exc) from exc
    await session.commit()
    return await get_assessment(session, org_id(membership), assessment.id) or assessment


@router.post("/attempts/{attempt_id}/outcomes/recalculate", response_model=list[OutcomeRead])
async def recalculate_attempt_outcomes(
    attempt_id: UUID,
    data: RecalculateRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> list[AssessmentOutcomeEvidence]:
    attempt = await load_attempt(session, org_id(membership), attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Tentativa não encontrada")
    attempt.grading_revision += 1
    rows = await recalculate_attempt_evidence(session, attempt=attempt)
    await session.commit()
    _ = (data, user)
    return rows


@router.post("/assignments/{assignment_id}/outcomes/recalculate")
async def recalculate_assignment_outcomes(
    assignment_id: UUID,
    data: RecalculateRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> dict[str, Any]:
    count = await recalculate_assignment(
        session,
        organization_id=org_id(membership),
        assignment_id=assignment_id,
    )
    await session.commit()
    return {"assignment_id": assignment_id, "recalculated_attempts": count, "reason": data.reason}


@router.get("/attempts/{attempt_id}/outcomes", response_model=list[OutcomeRead])
async def list_attempt_outcomes(
    attempt_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[AssessmentOutcomeEvidence]:
    return list(
        (
            await session.scalars(
                select(AssessmentOutcomeEvidence)
                .where(
                    AssessmentOutcomeEvidence.organization_id == org_id(membership),
                    AssessmentOutcomeEvidence.attempt_id == attempt_id,
                )
                .order_by(AssessmentOutcomeEvidence.dimension_type, AssessmentOutcomeEvidence.dimension_code)
            )
        ).all()
    )


@router.patch("/questions/{question_id}/annul", response_model=dict[str, Any])
async def set_question_annulment(
    question_id: UUID,
    data: QuestionAnnulmentRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        question = await annul_question(
            session,
            organization_id=org_id(membership),
            user_id=user.id,
            question_id=question_id,
            is_annulled=data.is_annulled,
            reason=data.reason,
            regrade_attempts=data.regrade_attempts,
        )
    except AssessmentError as exc:
        raise assessment_error(exc) from exc
    await session.commit()
    return {
        "question_id": question.id,
        "assignment_id": question.assignment_id,
        "is_annulled": question.is_annulled,
        "annulment_reason": question.annulment_reason,
    }


@router.post("/statistics/datasets", response_model=DatasetRead, status_code=201)
async def assessment_statistical_dataset(
    data: StatisticalDatasetFromAssessments,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
):
    try:
        dataset = await freeze_assessment_dataset(
            session,
            organization_id=org_id(membership),
            user_id=user.id,
            data=data,
        )
    except AssessmentError as exc:
        raise assessment_error(exc) from exc
    await session.commit()
    await session.refresh(dataset)
    return dataset


@router.get("/{assessment_id}/audit", response_model=list[AuditEventRead])
async def assessment_audit_log(
    assessment_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[AssessmentAuditEvent]:
    return list(
        (
            await session.scalars(
                select(AssessmentAuditEvent)
                .where(
                    AssessmentAuditEvent.organization_id == org_id(membership),
                    AssessmentAuditEvent.assessment_id == assessment_id,
                )
                .order_by(AssessmentAuditEvent.created_at.desc())
            )
        ).all()
    )


@router.get("/integrations/connectors")
async def list_connectors(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[dict[str, Any]]:
    rows = list(
        (
            await session.scalars(
                select(AssessmentConnector)
                .where(AssessmentConnector.organization_id == org_id(membership))
                .order_by(AssessmentConnector.created_at.desc())
            )
        ).all()
    )
    return [
        {
            "id": row.id,
            "name": row.name,
            "connector_type": row.connector_type,
            "status": row.status,
            "public_configuration": row.public_configuration,
            "external_system_key": row.external_system_key,
        }
        for row in rows
    ]


@router.post("/integrations/connectors", status_code=201)
async def create_connector(
    data: dict[str, Any],
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    connector_type = str(data.get("connector_type", "json_api"))
    allowed = {"csv", "xlsx", "json_api", "qti", "lti", "xapi", "scorm"}
    if connector_type not in allowed:
        raise HTTPException(status_code=422, detail="Tipo de conector não suportado")
    connector = AssessmentConnector(
        organization_id=org_id(membership),
        name=str(data.get("name", connector_type)).strip(),
        connector_type=connector_type,
        status="inactive",
        public_configuration=dict(data.get("public_configuration") or {}),
        external_system_key=data.get("external_system_key"),
        created_by_user_id=user.id,
    )
    session.add(connector)
    await session.commit()
    await session.refresh(connector)
    return {"id": connector.id, "name": connector.name, "connector_type": connector.connector_type, "status": connector.status}
