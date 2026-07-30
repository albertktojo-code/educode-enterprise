from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db_session
from app.models.ai_runtime import (
    AIActivityEvent,
    AIGenerationRequest,
    AIGenerationResult,
    AIGenerationReview,
    AIModel,
    AIModuleLink,
    AIModulePolicy,
    AIPromptTemplate,
    AIProvider,
)
from app.models.auth import Membership, OrganizationRole, User
from app.models.operations import BackgroundJob
from app.schemas.ai_runtime import (
    AIActivityEventRead,
    AIApplyResultRequest,
    AICapabilityRead,
    AIGenerationCreate,
    AIGenerationRequestRead,
    AIGenerationResultRead,
    AIModelCreate,
    AIModelRead,
    AIModuleLinkRead,
    AIModulePolicyRead,
    AIModulePolicyUpsert,
    AIPromptTemplateCreate,
    AIPromptTemplateRead,
    AIProviderCreate,
    AIProviderRead,
    AIReviewCreate,
    AIUsageSummary,
)
from app.services.ai.orchestrator import (
    MODULE_CAPABILITIES,
    AIOrchestrationError,
    apply_result_to_module,
    cancel_request,
    create_generation_request,
    get_policy,
    get_request,
    log_event,
    run_generation,
    usage_summary,
)
from app.services.operations import (
    create_job,
    find_cached_result,
    mark_queued,
    register_cached_result,
)

router = APIRouter(prefix="/ai", tags=["ai-fabric"])
ADMIN_ROLES = (OrganizationRole.OWNER, OrganizationRole.ADMIN)
TEACHER_ROLES = (OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.TEACHER)


def org_id(membership: Membership) -> UUID:
    return membership.organization_id


def orchestration_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/capabilities", response_model=list[AICapabilityRead])
async def capabilities(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[AICapabilityRead]:
    rows: list[AICapabilityRead] = []
    for module_name, actions in MODULE_CAPABILITIES.items():
        policy = await get_policy(session, org_id(membership), module_name)
        rows.append(
            AICapabilityRead(
                module_name=module_name,
                actions=actions if policy is None or not policy.allowed_actions else policy.allowed_actions,
                human_approval_required=True if policy is None else policy.human_approval_required,
                enabled=True if policy is None else policy.enabled,
                notes="A IA propõe; o EduCode valida; o usuário autorizado decide.",
            )
        )
    return rows


@router.get("/requests", response_model=list[AIGenerationRequestRead])
async def list_requests(
    module_name: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[AIGenerationRequest]:
    statement = (
        select(AIGenerationRequest)
        .where(AIGenerationRequest.organization_id == org_id(membership))
        .options(selectinload(AIGenerationRequest.results))
        .order_by(AIGenerationRequest.created_at.desc())
        .limit(limit)
    )
    if module_name:
        statement = statement.where(AIGenerationRequest.module_name == module_name)
    if status:
        statement = statement.where(AIGenerationRequest.status == status)
    return list((await session.scalars(statement)).all())


@router.post("/requests", response_model=AIGenerationRequestRead, status_code=201)
async def create_request(
    data: AIGenerationCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> AIGenerationRequest:
    try:
        request = await create_generation_request(
            session,
            organization_id=org_id(membership),
            user_id=user.id,
            data=data,
        )
    except AIOrchestrationError as exc:
        raise orchestration_error(exc) from exc
    cache_hit = None
    if bool(data.parameters.get("reuse_cache", True)):
        cache_hit = await find_cached_result(session, request)
        if cache_hit is not None:
            cloned = AIGenerationResult(
                request_id=request.id,
                organization_id=request.organization_id,
                result_type=cache_hit.result_type,
                structured_content=cache_hit.structured_content,
                text_content=cache_hit.text_content,
                storage_reference=cache_hit.storage_reference,
                validation_results={**cache_hit.validation_results, "semantic_cache_hit": True},
                safety_results=cache_hit.safety_results,
                review_status="approved",
                content_checksum=cache_hit.content_checksum,
            )
            session.add(cloned)
            request.status = "completed"
            request.completed_at = datetime.now(UTC)
            request.source_snapshot = {"semantic_cache_hit": True, "source_result_id": str(cache_hit.id)}
            await log_event(
                session,
                flow_id=request.flow_id,
                organization_id=request.organization_id,
                module_name=request.module_name,
                event_type="ai.request.cache_hit",
                request_id=request.id,
                user_id=user.id,
                data={"source_result_id": str(cache_hit.id)},
            )
    await session.commit()
    if data.queue_immediately and cache_hit is None:
        try:
            job, created = await create_job(
                session,
                organization_id=org_id(membership),
                user_id=user.id,
                job_type="ai_generation",
                module_name=request.module_name,
                entity_type="ai_generation_request",
                entity_id=request.id,
                ai_flow_id=request.flow_id,
                priority=int(data.parameters.get("priority", 50)),
                total_steps=4,
                max_retries=int(data.parameters.get("max_retries", 3)),
                idempotency_key=f"ai-request:{request.id}",
                input_snapshot={"request_id": str(request.id)},
                estimated_cost=request.estimated_cost,
            )
        except ValueError as exc:
            request.status = "pending"
            request.error_message = str(exc)
            await session.commit()
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        await session.commit()
        if created:
            await mark_queued(session, job)
            await session.commit()
    return await get_request(session, org_id(membership), request.id) or request


@router.get("/requests/{request_id}", response_model=AIGenerationRequestRead)
async def read_request(
    request_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> AIGenerationRequest:
    request = await get_request(session, org_id(membership), request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Solicitação de IA não encontrada")
    return request


@router.post("/requests/{request_id}/run", response_model=AIGenerationRequestRead)
async def execute_request(
    request_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> AIGenerationRequest:
    try:
        request = await run_generation(session, organization_id=org_id(membership), request_id=request_id)
    except AIOrchestrationError as exc:
        raise orchestration_error(exc) from exc
    await session.commit()
    return request


@router.post("/requests/{request_id}/cancel", response_model=AIGenerationRequestRead)
async def cancel_generation(
    request_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> AIGenerationRequest:
    try:
        request = await cancel_request(
            session,
            organization_id=org_id(membership),
            request_id=request_id,
            user_id=user.id,
        )
    except AIOrchestrationError as exc:
        raise orchestration_error(exc) from exc
    linked_job = await session.scalar(
        select(BackgroundJob).where(
            BackgroundJob.organization_id == org_id(membership),
            BackgroundJob.entity_type == "ai_generation_request",
            BackgroundJob.entity_id == request.id,
            BackgroundJob.status.not_in(["completed", "failed", "cancelled", "expired"]),
        )
    )
    if linked_job is not None:
        linked_job.cancel_requested = True
        linked_job.current_step = "Cancelamento solicitado pelo AI Fabric"
    await session.commit()
    return request


@router.post("/results/{result_id}/review", response_model=AIGenerationResultRead)
async def review_result(
    result_id: UUID,
    data: AIReviewCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> AIGenerationResult:
    result = await session.scalar(
        select(AIGenerationResult)
        .where(AIGenerationResult.id == result_id, AIGenerationResult.organization_id == org_id(membership))
        .options(selectinload(AIGenerationResult.request))
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Resultado não encontrado")
    existing = await session.scalar(
        select(AIGenerationReview).where(
            AIGenerationReview.result_id == result.id,
            AIGenerationReview.reviewed_by_user_id == user.id,
        )
    )
    if existing is None:
        existing = AIGenerationReview(
            organization_id=org_id(membership),
            result_id=result.id,
            reviewed_by_user_id=user.id,
            decision=data.decision,
        )
        session.add(existing)
    existing.decision = data.decision
    existing.correctness_rating = data.correctness_rating
    existing.pedagogical_rating = data.pedagogical_rating
    existing.creativity_rating = data.creativity_rating
    existing.safety_rating = data.safety_rating
    existing.comments = data.comments
    result.review_status = data.decision
    if data.decision == "approved":
        await register_cached_result(session, result.request, result)
    await log_event(
        session,
        flow_id=result.request.flow_id,
        organization_id=org_id(membership),
        module_name=result.request.module_name,
        event_type="ai.result.reviewed",
        request_id=result.request_id,
        user_id=user.id,
        data={"result_id": str(result.id), "decision": data.decision},
    )
    await session.commit()
    return result


@router.post("/results/{result_id}/apply", response_model=AIGenerationResultRead)
async def apply_result(
    result_id: UUID,
    data: AIApplyResultRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> AIGenerationResult:
    try:
        result = await apply_result_to_module(
            session,
            organization_id=org_id(membership),
            user_id=user.id,
            result_id=result_id,
            target_type=data.target_type,
            target_id=data.target_id,
            options=data.options,
        )
    except AIOrchestrationError as exc:
        raise orchestration_error(exc) from exc
    await session.commit()
    return result


@router.get("/flows/{flow_id}", response_model=list[AIActivityEventRead])
async def flow_events(
    flow_id: str,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[AIActivityEvent]:
    return list(
        (
            await session.scalars(
                select(AIActivityEvent)
                .where(
                    AIActivityEvent.organization_id == org_id(membership),
                    AIActivityEvent.flow_id == flow_id,
                )
                .order_by(AIActivityEvent.created_at)
            )
        ).all()
    )


@router.get("/links", response_model=list[AIModuleLinkRead])
async def module_links(
    target_type: str | None = Query(default=None),
    target_id: UUID | None = Query(default=None),
    module_name: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[AIModuleLink]:
    statement = select(AIModuleLink).where(AIModuleLink.organization_id == org_id(membership))
    if target_type:
        statement = statement.where(AIModuleLink.target_type == target_type)
    if target_id:
        statement = statement.where(AIModuleLink.target_id == target_id)
    if module_name:
        statement = statement.where(AIModuleLink.module_name == module_name)
    return list((await session.scalars(statement.order_by(AIModuleLink.created_at.desc()).limit(200))).all())


@router.get("/admin/providers", response_model=list[AIProviderRead])
async def list_providers(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[AIProvider]:
    return list(
        (
            await session.scalars(
                select(AIProvider)
                .where(AIProvider.organization_id == org_id(membership))
                .order_by(AIProvider.name)
            )
        ).all()
    )


@router.post("/admin/providers", response_model=AIProviderRead, status_code=201)
async def create_provider(
    data: AIProviderCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> AIProvider:
    provider = AIProvider(
        organization_id=org_id(membership),
        name=data.name,
        provider_type=data.provider_type,
        public_configuration=data.public_configuration,
        secret_env_var=data.secret_env_var,
        base_url=data.base_url,
        timeout_seconds=data.timeout_seconds,
        created_by_user_id=user.id,
    )
    session.add(provider)
    await session.commit()
    return provider


@router.get("/admin/models", response_model=list[AIModelRead])
async def list_models(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[AIModel]:
    return list(
        (
            await session.scalars(
                select(AIModel)
                .where(AIModel.organization_id == org_id(membership))
                .order_by(AIModel.is_default.desc(), AIModel.name)
            )
        ).all()
    )


@router.post("/admin/models", response_model=AIModelRead, status_code=201)
async def create_model(
    data: AIModelCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> AIModel:
    provider = await session.scalar(
        select(AIProvider).where(
            AIProvider.id == data.provider_id,
            AIProvider.organization_id == org_id(membership),
        )
    )
    if provider is None:
        raise HTTPException(status_code=404, detail="Provedor não encontrado")
    if data.is_default:
        for row in (
            await session.scalars(
                select(AIModel).where(AIModel.organization_id == org_id(membership))
            )
        ).all():
            row.is_default = False
    model = AIModel(
        organization_id=org_id(membership),
        provider_id=provider.id,
        name=data.name,
        model_identifier=data.model_identifier,
        capabilities=data.capabilities,
        configuration=data.configuration,
        is_default=data.is_default,
        input_unit_cost=data.input_unit_cost,
        output_unit_cost=data.output_unit_cost,
        image_unit_cost=data.image_unit_cost,
    )
    session.add(model)
    await session.commit()
    return model


@router.get("/admin/prompts", response_model=list[AIPromptTemplateRead])
async def list_prompts(
    purpose: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[AIPromptTemplate]:
    statement = select(AIPromptTemplate).where(AIPromptTemplate.organization_id == org_id(membership))
    if purpose:
        statement = statement.where(AIPromptTemplate.purpose == purpose)
    return list((await session.scalars(statement.order_by(AIPromptTemplate.purpose, AIPromptTemplate.version.desc()))).all())


@router.post("/admin/prompts", response_model=AIPromptTemplateRead, status_code=201)
async def create_prompt(
    data: AIPromptTemplateCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> AIPromptTemplate:
    prompt = AIPromptTemplate(
        organization_id=org_id(membership),
        purpose=data.purpose,
        name=data.name,
        version=data.version,
        system_instructions=data.system_instructions,
        template_content=data.template_content,
        required_variables=data.required_variables,
        output_schema=data.output_schema,
        status=data.status,
        recommended_model_id=data.recommended_model_id,
        created_by_user_id=user.id,
        approved_by_user_id=user.id if data.status == "approved" else None,
    )
    session.add(prompt)
    await session.commit()
    return prompt


@router.get("/admin/policies", response_model=list[AIModulePolicyRead])
async def list_policies(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[AIModulePolicy]:
    return list(
        (
            await session.scalars(
                select(AIModulePolicy)
                .where(AIModulePolicy.organization_id == org_id(membership))
                .order_by(AIModulePolicy.module_name)
            )
        ).all()
    )


@router.put("/admin/policies/{module_name}", response_model=AIModulePolicyRead)
async def upsert_policy(
    module_name: str,
    data: AIModulePolicyUpsert,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> AIModulePolicy:
    if module_name != data.module_name:
        raise HTTPException(status_code=422, detail="O módulo da rota difere do corpo")
    if module_name not in MODULE_CAPABILITIES:
        raise HTTPException(status_code=422, detail="Módulo desconhecido")
    policy = await get_policy(session, org_id(membership), module_name)
    if policy is None:
        policy = AIModulePolicy(
            organization_id=org_id(membership),
            module_name=module_name,
            updated_by_user_id=user.id,
        )
        session.add(policy)
    policy.enabled = data.enabled
    policy.allowed_actions = data.allowed_actions
    policy.allowed_model_ids = [str(item) for item in data.allowed_model_ids]
    policy.human_approval_required = data.human_approval_required
    policy.daily_request_limit = data.daily_request_limit
    policy.monthly_cost_limit = data.monthly_cost_limit
    policy.allow_student_data = data.allow_student_data
    policy.allow_real_person_images = data.allow_real_person_images
    policy.fallback_mode = data.fallback_mode
    policy.policy_configuration = data.policy_configuration
    policy.updated_by_user_id = user.id
    await session.commit()
    return policy


@router.get("/admin/usage", response_model=AIUsageSummary)
async def admin_usage(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> AIUsageSummary:
    return AIUsageSummary(**(await usage_summary(session, org_id(membership))))
