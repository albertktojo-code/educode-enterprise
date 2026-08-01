from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.ai_runtime import (
    AIActivityEvent,
    AIGenerationRequest,
    AIGenerationResult,
    AIModel,
    AIModuleLink,
    AIModulePolicy,
    AIPromptTemplate,
    AIProvider,
    AIRequestStatus,
    AIUsageRecord,
)
from app.models.assessment import Assessment, QuestionBankStatus
from app.models.analytics import LearningAlert, LearningIntervention
from app.models.assets import InstitutionalAsset
from app.models.comic import GeneratedComic
from app.models.education import Project
from app.models.pedagogy import LearningUnit
from app.models.delivery import QuestionType
from app.models.rag import RagContext
from app.models.statistics import StatisticalAnalysis, StatisticalReport
from app.models.studio import TeacherStudioDraft
from app.schemas.ai_runtime import AIGenerationCreate
from app.schemas.assessment import BankItemCreate
from app.services.ai.providers import (
    AIProviderError,
    BaseRuntimeProvider,
    GenericHTTPRuntimeProvider,
    MockRuntimeProvider,
    ProviderOutput,
)
from app.services.ai.safety import redact_personal_data, scan_untrusted_text
from app.services.ai.validation import validate_output
from app.services.assessment import add_item_to_assessment, create_bank_item


class AIOrchestrationError(ValueError):
    pass


MODULE_CAPABILITIES: dict[str, list[str]] = {
    "planning": ["generate_lesson_plan", "adapt_learning_sequence", "review_alignment"],
    "rag": ["summarize_sources", "extract_facts", "draft_from_sources"],
    "comics": ["generate_script", "generate_panel", "generate_image", "regenerate_element"],
    "assets": ["describe_asset", "create_character_profile", "suggest_tags"],
    "assessments": ["generate_questions", "generate_rubric", "generate_feedback"],
    "grading": ["suggest_discursive_grade", "generate_feedback"],
    "analytics": ["explain_indicators", "suggest_intervention", "draft_student_summary"],
    "interventions": ["create_intervention", "adapt_material"],
    "statistics": ["explain_result", "draft_report", "suggest_limitations"],
    "reports": ["draft_pedagogical_report", "draft_research_report", "describe_chart"],
    "accessibility": ["generate_alt_text", "simplify_language", "create_audio_description"],
}

_BUILTIN_TEMPLATES: dict[str, tuple[str, str]] = {
    "lesson_plan": (
        "Você é um assistente pedagógico. Gere apenas um rascunho revisável e preserve BNCC e PC.",
        "Crie um plano de aula usando os dados: {input_json}. Fontes autorizadas: {rag_context}",
    ),
    "comic_script": (
        "Crie uma HQ educativa coerente, criativa e adequada à faixa etária. Não incorpore texto na imagem.",
        "Produza roteiro estruturado para HQ usando: {input_json}. Fontes: {rag_context}",
    ),
    "assessment_questions": (
        "Crie questões revisáveis. Gabarito e explicação devem ser coerentes; não publique automaticamente.",
        "Gere questões a partir de: {input_json}. Use somente o contexto autorizado: {rag_context}",
    ),
    "intervention": (
        "Proponha intervenção pedagógica explicável e baseada em evidências. O professor decide.",
        "Evidências e preferências: {input_json}",
    ),
    "statistical_report": (
        "Nunca calcule estatísticas. Apenas interprete resultados determinísticos fornecidos e evite causalidade indevida.",
        "Redija rascunho usando exclusivamente estes resultados: {input_json}",
    ),
    "generic": (
        "Produza conteúdo educacional revisável, seguro, rastreável e adequado ao contexto informado.",
        "Solicitação: {input_json}. Contexto autorizado: {rag_context}",
    ),
}


def utcnow() -> datetime:
    return datetime.now(UTC)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def checksum(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def purpose_for(module_name: str, action_name: str, input_data: dict[str, Any]) -> str:
    explicit = input_data.get("purpose")
    if isinstance(explicit, str) and explicit:
        return explicit
    action = action_name.casefold()
    if module_name == "assessments" or "question" in action:
        return "assessment_questions"
    if module_name == "comics" or "comic" in action or "hq" in action:
        return "comic_script"
    if module_name in {"analytics", "interventions"} or "intervention" in action:
        return "intervention"
    if module_name in {"statistics", "reports"}:
        return "statistical_report"
    if module_name == "planning":
        return "lesson_plan"
    return "generic"


async def log_event(
    session: AsyncSession,
    *,
    flow_id: str,
    organization_id: UUID,
    module_name: str,
    event_type: str,
    request_id: UUID | None,
    user_id: UUID | None,
    data: dict[str, Any] | None = None,
) -> None:
    session.add(
        AIActivityEvent(
            flow_id=flow_id,
            organization_id=organization_id,
            request_id=request_id,
            module_name=module_name,
            event_type=event_type,
            event_data=data or {},
            created_by_user_id=user_id,
        )
    )


async def get_policy(session: AsyncSession, organization_id: UUID, module_name: str) -> AIModulePolicy | None:
    return await session.scalar(
        select(AIModulePolicy).where(
            AIModulePolicy.organization_id == organization_id,
            AIModulePolicy.module_name == module_name,
        )
    )


async def _enforce_policy(
    session: AsyncSession,
    *,
    organization_id: UUID,
    module_name: str,
    action_name: str,
    model_id: UUID | None,
) -> AIModulePolicy | None:
    policy = await get_policy(session, organization_id, module_name)
    if policy is None:
        return None
    if not policy.enabled:
        raise AIOrchestrationError(f"A IA está desabilitada para o módulo {module_name}")
    if policy.allowed_actions and action_name not in policy.allowed_actions:
        raise AIOrchestrationError("A ação de IA não está autorizada pela política institucional")
    if model_id and policy.allowed_model_ids and str(model_id) not in policy.allowed_model_ids:
        raise AIOrchestrationError("O modelo selecionado não está autorizado para este módulo")
    day_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    count = await session.scalar(
        select(func.count(AIGenerationRequest.id)).where(
            AIGenerationRequest.organization_id == organization_id,
            AIGenerationRequest.module_name == module_name,
            AIGenerationRequest.created_at >= day_start,
        )
    )
    if policy.daily_request_limit and int(count or 0) >= policy.daily_request_limit:
        raise AIOrchestrationError("Limite diário de solicitações de IA atingido")
    month_start = day_start.replace(day=1)
    cost = await session.scalar(
        select(func.coalesce(func.sum(AIUsageRecord.estimated_cost), 0.0)).where(
            AIUsageRecord.organization_id == organization_id,
            AIUsageRecord.created_at >= month_start,
        )
    )
    if policy.monthly_cost_limit and float(cost or 0.0) >= policy.monthly_cost_limit:
        raise AIOrchestrationError("Limite mensal de custos de IA atingido")
    return policy


_TARGET_MODELS: dict[str, type[Any]] = {
    "assessment": Assessment,
    "project": Project,
    "comic": GeneratedComic,
    "institutional_asset": InstitutionalAsset,
    "learning_alert": LearningAlert,
    "learning_intervention": LearningIntervention,
    "statistical_analysis": StatisticalAnalysis,
    "statistical_report": StatisticalReport,
    "rag_context": RagContext,
    "learning_unit": LearningUnit,
    "teacher_studio_draft": TeacherStudioDraft,
}


async def ensure_target_exists(
    session: AsyncSession, *, organization_id: UUID, target_type: str, target_id: UUID
) -> None:
    model = _TARGET_MODELS.get(target_type)
    if model is None:
        raise AIOrchestrationError("Tipo de destino não suportado")
    row = await session.scalar(
        select(model).where(model.id == target_id, model.organization_id == organization_id)
    )
    if row is None:
        raise AIOrchestrationError("Entidade de destino não encontrada na organização ativa")


async def create_generation_request(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    data: AIGenerationCreate,
) -> AIGenerationRequest:
    if data.module_name not in MODULE_CAPABILITIES:
        raise AIOrchestrationError("Módulo de IA desconhecido")
    if data.action_name not in MODULE_CAPABILITIES[data.module_name]:
        raise AIOrchestrationError("Ação não suportada pelo adaptador do módulo")
    if data.target_type and data.target_id:
        await ensure_target_exists(
            session,
            organization_id=organization_id,
            target_type=data.target_type,
            target_id=data.target_id,
        )
    elif data.target_type or data.target_id:
        raise AIOrchestrationError("Tipo e identificador de destino devem ser informados juntos")
    policy = await _enforce_policy(
        session,
        organization_id=organization_id,
        module_name=data.module_name,
        action_name=data.action_name,
        model_id=data.model_id,
    )
    from app.institutional_governance.services import (
        GovernanceExecutionError,
        assert_ai_execution_allowed,
    )

    try:
        governance_checks = await assert_ai_execution_allowed(
            session,
            organization_id=organization_id,
            enforcement_mode=get_settings().governance_enforcement_mode,
            model_id=data.model_id,
            prompt_template_id=data.prompt_template_id,
            module_policy_id=policy.id if policy else None,
        )
    except GovernanceExecutionError as error:
        raise AIOrchestrationError(str(error)) from error
    sanitized_input = redact_personal_data(data.input_data) if not (policy and policy.allow_student_data) else data.input_data
    scan = scan_untrusted_text(canonical_json(sanitized_input))
    if scan["prompt_injection_detected"]:
        raise AIOrchestrationError("A entrada contém instruções potencialmente maliciosas")
    flow_id = f"AI-FLOW-{utcnow():%Y%m%d}-{uuid4().hex[:12].upper()}"
    request = AIGenerationRequest(
        flow_id=flow_id,
        organization_id=organization_id,
        requested_by_user_id=user_id,
        module_name=data.module_name,
        action_name=data.action_name,
        request_type=data.request_type,
        target_type=data.target_type,
        target_id=data.target_id,
        provider_id=data.provider_id,
        model_id=data.model_id,
        prompt_template_id=data.prompt_template_id,
        rag_context_id=data.rag_context_id,
        status=AIRequestStatus.QUEUED.value if data.queue_immediately else AIRequestStatus.PENDING.value,
        input_snapshot=sanitized_input,
        parameters=data.parameters,
        safety_summary={
            **scan,
            "governance_checks": governance_checks,
            "governance_enforcement_mode": (
                get_settings().governance_enforcement_mode
            ),
        },
        queued_at=utcnow() if data.queue_immediately else None,
    )
    session.add(request)
    await session.flush()
    if data.target_type and data.target_id:
        session.add(
            AIModuleLink(
                organization_id=organization_id,
                request_id=request.id,
                module_name=data.module_name,
                target_type=data.target_type,
                target_id=data.target_id,
                relation_type="context_target",
                status="pending",
                link_metadata={"action": data.action_name},
                created_by_user_id=user_id,
            )
        )
    await log_event(
        session,
        flow_id=flow_id,
        organization_id=organization_id,
        module_name=data.module_name,
        event_type="ai.request.created",
        request_id=request.id,
        user_id=user_id,
        data={"action": data.action_name, "target_type": data.target_type, "target_id": str(data.target_id) if data.target_id else None},
    )
    return request


async def get_request(
    session: AsyncSession, organization_id: UUID, request_id: UUID
) -> AIGenerationRequest | None:
    return await session.scalar(
        select(AIGenerationRequest)
        .where(
            AIGenerationRequest.id == request_id,
            AIGenerationRequest.organization_id == organization_id,
        )
        .options(selectinload(AIGenerationRequest.results))
    )


async def _resolve_model_and_provider(
    session: AsyncSession, request: AIGenerationRequest
) -> tuple[AIModel | None, AIProvider | None, BaseRuntimeProvider]:
    settings = get_settings()
    model: AIModel | None = None
    provider: AIProvider | None = None
    if request.model_id:
        model = await session.scalar(
            select(AIModel)
            .where(AIModel.id == request.model_id, AIModel.organization_id == request.organization_id)
            .options(selectinload(AIModel.provider))
        )
    if model:
        provider = model.provider
    elif request.provider_id:
        provider = await session.scalar(
            select(AIProvider).where(
                AIProvider.id == request.provider_id,
                AIProvider.organization_id == request.organization_id,
            )
        )
        if provider:
            model = await session.scalar(
                select(AIModel).where(
                    AIModel.provider_id == provider.id,
                    AIModel.is_active.is_(True),
                ).order_by(AIModel.is_default.desc(), AIModel.created_at)
            )
    else:
        model = await session.scalar(
            select(AIModel)
            .where(AIModel.organization_id == request.organization_id, AIModel.is_active.is_(True))
            .options(selectinload(AIModel.provider))
            .order_by(AIModel.is_default.desc(), AIModel.created_at)
        )
        if model:
            provider = model.provider
    if settings.ai_execution_mode == "mock":
        runtime = MockRuntimeProvider(name="Mock interno EduCode", model_identifier="educode-mock-v2")
        return None, None, runtime
    if settings.ai_execution_mode == "real" and (provider is None or model is None):
        raise AIProviderError("Modo real exige provedor e modelo ativos configurados")
    if provider and provider.status != "active":
        raise AIProviderError("O provedor selecionado não está ativo")
    if settings.ai_execution_mode == "real" and provider and provider.provider_type == "mock":
        raise AIProviderError("Modo real não permite provedor mock")
    if provider and model and provider.provider_type == "generic_http":
        if not provider.base_url:
            raise AIProviderError("Provedor HTTP sem URL base")
        runtime = GenericHTTPRuntimeProvider(
            name=provider.name,
            model_identifier=model.model_identifier,
            base_url=provider.base_url,
            secret_env_var=provider.secret_env_var,
            timeout_seconds=provider.timeout_seconds,
            configuration={**provider.public_configuration, **model.configuration},
        )
        return model, provider, runtime
    runtime = MockRuntimeProvider(
        name=provider.name if provider else "Mock interno EduCode",
        model_identifier=model.model_identifier if model else "educode-mock-v2",
    )
    return model, provider, runtime


async def _resolve_template(
    session: AsyncSession, request: AIGenerationRequest, purpose: str
) -> tuple[str, str, dict[str, Any]]:
    template: AIPromptTemplate | None = None
    if request.prompt_template_id:
        template = await session.scalar(
            select(AIPromptTemplate).where(
                AIPromptTemplate.id == request.prompt_template_id,
                AIPromptTemplate.organization_id == request.organization_id,
            )
        )
    if template is None:
        template = await session.scalar(
            select(AIPromptTemplate)
            .where(
                AIPromptTemplate.organization_id == request.organization_id,
                AIPromptTemplate.purpose == purpose,
                AIPromptTemplate.status == "approved",
            )
            .order_by(AIPromptTemplate.version.desc())
        )
    if template:
        missing = [key for key in template.required_variables if key not in request.input_snapshot]
        if missing:
            raise AIOrchestrationError(f"Variáveis obrigatórias ausentes: {', '.join(missing)}")
        return template.system_instructions, template.template_content, template.output_schema
    system, content = _BUILTIN_TEMPLATES.get(purpose, _BUILTIN_TEMPLATES["generic"])
    return system, content, {}


async def _rag_snapshot(session: AsyncSession, request: AIGenerationRequest) -> tuple[str, dict[str, Any]]:
    if not request.rag_context_id:
        return "Nenhum contexto RAG selecionado.", {}
    context = await session.scalar(
        select(RagContext)
        .where(
            RagContext.id == request.rag_context_id,
            RagContext.organization_id == request.organization_id,
        )
        .options(
            selectinload(RagContext.sources),
            selectinload(RagContext.facts),
            selectinload(RagContext.rules),
            selectinload(RagContext.conflicts),
        )
    )
    if context is None:
        raise AIOrchestrationError("Contexto RAG não encontrado")
    blocked = [source for source in context.sources if str(source.safety_status) == "blocked"]
    included = [source for source in context.sources if source.is_included and source not in blocked]
    source_text = "\n\n".join(
        f"[{source.citation_code}] {source.citation_label}\n{source.content_snapshot}"
        for source in included
    )
    snapshot = {
        "rag_context_id": str(context.id),
        "context_version": context.context_version,
        "status": str(context.status),
        "quality_score": context.quality_score,
        "citations": [
            {
                "code": source.citation_code,
                "label": source.citation_label,
                "page_start": source.page_start,
                "page_end": source.page_end,
                "safety": str(source.safety_status),
            }
            for source in included
        ],
        "mandatory_facts": [fact.statement for fact in context.facts if fact.is_mandatory],
        "rules": [rule.rule_text for rule in context.rules],
        "open_conflicts": [conflict.description for conflict in context.conflicts if str(conflict.status) == "open"],
    }
    scan = scan_untrusted_text(source_text)
    if scan["prompt_injection_detected"]:
        raise AIOrchestrationError("O contexto RAG contém uma possível tentativa de prompt injection")
    return source_text or context.assembled_context_text, snapshot


def _render_template(template: str, input_data: dict[str, Any], rag_context: str) -> str:
    replacements = {
        "input_json": json.dumps(input_data, ensure_ascii=False, indent=2, default=str),
        "rag_context": rag_context,
    }
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace("{" + key + "}", value)
    for key, value in input_data.items():
        rendered = rendered.replace("{" + key + "}", str(value))
    return rendered


def _estimate_cost(model: AIModel | None, output: ProviderOutput) -> float:
    if model is None:
        return 0.0
    return round(
        output.input_units * model.input_unit_cost
        + output.output_units * model.output_unit_cost
        + output.image_count * model.image_unit_cost,
        8,
    )


async def run_generation(
    session: AsyncSession,
    *,
    organization_id: UUID,
    request_id: UUID,
) -> AIGenerationRequest:
    request = await get_request(session, organization_id, request_id)
    if request is None:
        raise AIOrchestrationError("Solicitação de IA não encontrada")
    if request.status in {AIRequestStatus.COMPLETED.value, AIRequestStatus.CANCELLED.value}:
        return request
    request.status = AIRequestStatus.PROCESSING.value
    request.started_at = utcnow()
    await log_event(
        session,
        flow_id=request.flow_id,
        organization_id=organization_id,
        module_name=request.module_name,
        event_type="ai.request.processing",
        request_id=request.id,
        user_id=request.requested_by_user_id,
    )
    await session.flush()
    started = time.perf_counter()
    try:
        policy = await _enforce_policy(
            session,
            organization_id=organization_id,
            module_name=request.module_name,
            action_name=request.action_name,
            model_id=request.model_id,
        )
        purpose = purpose_for(request.module_name, request.action_name, request.input_snapshot)
        system, template, output_schema = await _resolve_template(session, request, purpose)
        rag_text, source_snapshot = await _rag_snapshot(session, request)
        prompt = _render_template(template, request.input_snapshot, rag_text)
        combined_scan = scan_untrusted_text(system + "\n" + prompt)
        if combined_scan["prompt_injection_detected"]:
            raise AIOrchestrationError("Prompt final bloqueado pela camada de segurança")
        model, provider, runtime = await _resolve_model_and_provider(session, request)
        parameters = {
            **request.parameters,
            "purpose": purpose,
            "topic": request.input_snapshot.get("topic") or request.input_snapshot.get("title"),
            "quantity": request.input_snapshot.get("quantity") or request.parameters.get("quantity"),
            "difficulty": request.input_snapshot.get("difficulty") or request.parameters.get("difficulty"),
            "curriculum_skills": request.input_snapshot.get("curriculum_skill_codes", []),
            "ct_pillars": request.input_snapshot.get("ct_pillar_codes", []),
            "panel_count": request.input_snapshot.get("panel_count") or request.parameters.get("panel_count"),
            "pedagogical_objective": request.input_snapshot.get("pedagogical_objective", ""),
            "evidence_summary": request.input_snapshot.get("evidence_summary", ""),
            "limitations": request.input_snapshot.get("limitations", []),
        }
        fallback_used = False
        try:
            output = await runtime.generate(
                request_type=request.request_type,
                system_instructions=system,
                prompt=prompt,
                output_schema=output_schema,
                parameters=parameters,
            )
        except AIProviderError:
            fallback_mode = policy.fallback_mode if policy else "mock"
            if (
                fallback_mode == "mock"
                and not isinstance(runtime, MockRuntimeProvider)
                and get_settings().ai_execution_mode != "real"
            ):
                runtime = MockRuntimeProvider(
                    name="Mock de contingência EduCode", model_identifier="educode-mock-v2"
                )
                output = await runtime.generate(
                    request_type=request.request_type,
                    system_instructions=system,
                    prompt=prompt,
                    output_schema=output_schema,
                    parameters=parameters,
                )
                fallback_used = True
            else:
                raise
        request.status = AIRequestStatus.VALIDATING.value
        validation = validate_output(purpose, output.structured)
        safety = {
            **combined_scan,
            "provider_mode": "mock" if fallback_used or provider is None or provider.provider_type == "mock" else provider.provider_type,
            "fallback_used": fallback_used,
            "human_approval_required": True if policy is None else policy.human_approval_required,
        }
        if not validation["valid"]:
            raise AIOrchestrationError("Saída inválida: " + "; ".join(validation["errors"]))
        result = AIGenerationResult(
            request_id=request.id,
            organization_id=organization_id,
            result_type=request.request_type,
            structured_content=output.structured,
            text_content=output.text,
            storage_reference=output.storage_reference,
            validation_results=validation,
            safety_results=safety,
            content_checksum=checksum({"structured": output.structured, "text": output.text, "storage": output.storage_reference}),
        )
        session.add(result)
        estimated_cost = _estimate_cost(model, output)
        request.estimated_cost = estimated_cost
        request.validation_summary = validation
        request.safety_summary = safety
        request.source_snapshot = source_snapshot
        request.status = AIRequestStatus.COMPLETED.value
        request.completed_at = utcnow()
        processing_ms = int((time.perf_counter() - started) * 1000)
        session.add(
            AIUsageRecord(
                organization_id=organization_id,
                request_id=request.id,
                provider_name=provider.name if provider else "Mock interno EduCode",
                model_identifier=model.model_identifier if model else "educode-mock-v2",
                input_units=output.input_units,
                output_units=output.output_units,
                image_count=output.image_count,
                estimated_cost=estimated_cost,
                processing_time_ms=processing_ms,
            )
        )
        await session.flush()
        await log_event(
            session,
            flow_id=request.flow_id,
            organization_id=organization_id,
            module_name=request.module_name,
            event_type="ai.request.completed",
            request_id=request.id,
            user_id=request.requested_by_user_id,
            data={
                "result_id": str(result.id),
                "provider": provider.name if provider else "mock",
                "model": model.model_identifier if model else "educode-mock-v2",
                "cost": estimated_cost,
                "citations": source_snapshot.get("citations", []),
                "fallback_used": fallback_used,
            },
        )
    except (AIProviderError, AIOrchestrationError, KeyError, TypeError, ValueError) as exc:
        request.status = AIRequestStatus.FAILED.value
        request.error_message = str(exc)
        request.completed_at = utcnow()
        await log_event(
            session,
            flow_id=request.flow_id,
            organization_id=organization_id,
            module_name=request.module_name,
            event_type="ai.request.failed",
            request_id=request.id,
            user_id=request.requested_by_user_id,
            data={"error": str(exc)},
        )
    await session.flush()
    return await get_request(session, organization_id, request.id) or request


async def cancel_request(
    session: AsyncSession, *, organization_id: UUID, request_id: UUID, user_id: UUID
) -> AIGenerationRequest:
    request = await get_request(session, organization_id, request_id)
    if request is None:
        raise AIOrchestrationError("Solicitação não encontrada")
    if request.status in {AIRequestStatus.COMPLETED.value, AIRequestStatus.FAILED.value}:
        raise AIOrchestrationError("A solicitação já foi encerrada")
    request.status = AIRequestStatus.CANCELLED.value
    request.completed_at = utcnow()
    await log_event(
        session,
        flow_id=request.flow_id,
        organization_id=organization_id,
        module_name=request.module_name,
        event_type="ai.request.cancelled",
        request_id=request.id,
        user_id=user_id,
    )
    await session.flush()
    return request


async def apply_result_to_module(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    result_id: UUID,
    target_type: str,
    target_id: UUID | None,
    options: dict[str, Any],
) -> AIGenerationResult:
    result = await session.scalar(
        select(AIGenerationResult)
        .where(AIGenerationResult.id == result_id, AIGenerationResult.organization_id == organization_id)
        .options(selectinload(AIGenerationResult.request))
    )
    if result is None:
        raise AIOrchestrationError("Resultado não encontrado")
    policy = await get_policy(session, organization_id, result.request.module_name)
    approval_required = True if policy is None else policy.human_approval_required
    if approval_required and result.review_status != "approved":
        raise AIOrchestrationError("O resultado precisa ser aprovado antes da aplicação")
    if result.applied_to_module:
        return result
    if target_id is not None:
        await ensure_target_exists(
            session,
            organization_id=organization_id,
            target_type=target_type,
            target_id=target_id,
        )
    application: dict[str, Any] = {"target_type": target_type, "target_id": str(target_id) if target_id else None}
    if target_type == "assessment":
        if target_id is None:
            raise AIOrchestrationError("Informe a avaliação de destino")
        questions = result.structured_content.get("questions")
        if not isinstance(questions, list) or not questions:
            raise AIOrchestrationError("O resultado não contém questões aplicáveis")
        item_ids: list[str] = []
        for question in questions:
            try:
                item_type = QuestionType(str(question.get("item_type", "multiple_choice")))
            except ValueError as exc:
                raise AIOrchestrationError("Tipo de questão não suportado") from exc
            bank_item = await create_bank_item(
                session,
                organization_id=organization_id,
                user_id=user_id,
                data=BankItemCreate(
                    title=str(question.get("title", "Questão gerada por IA")),
                    item_type=item_type,
                    prompt=str(question.get("prompt", "")),
                    options=list(question.get("options") or []),
                    answer_key=dict(question.get("answer_key") or {}),
                    explanation=str(question.get("explanation", "")),
                    points=float(question.get("points", 1.0)),
                    difficulty=str(question.get("difficulty", "medium")),
                    curriculum_skill_codes=list(question.get("curriculum_skill_codes") or []),
                    ct_pillar_codes=list(question.get("ct_pillar_codes") or []),
                    source_type="ai",
                    source_metadata={"ai_flow_id": result.request.flow_id, "ai_result_id": str(result.id)},
                    ai_generation_metadata={
                        "request_id": str(result.request_id),
                        "result_checksum": result.content_checksum,
                        "teacher_review_required": True,
                    },
                    requires_manual_grading=bool(question.get("requires_manual_grading", False)),
                ),
                status=QuestionBankStatus.DRAFT.value,
            )
            await add_item_to_assessment(
                session,
                organization_id=organization_id,
                user_id=user_id,
                assessment_id=target_id,
                item_id=bank_item.id,
                position=None,
                points_override=None,
            )
            item_ids.append(str(bank_item.id))
        application["created_question_ids"] = item_ids
    else:
        application["adapter"] = f"{target_type}_adapter"
        application["note"] = "Resultado vinculado ao módulo; a edição final permanece sob controle humano."
        application["options"] = options
    result.applied_to_module = True
    result.application_snapshot = application
    if target_id is not None:
        session.add(
            AIModuleLink(
                organization_id=organization_id,
                request_id=result.request_id,
                result_id=result.id,
                module_name=result.request.module_name,
                target_type=target_type,
                target_id=target_id,
                relation_type="generated_output",
                status="applied",
                link_metadata=application,
                created_by_user_id=user_id,
            )
        )
    await log_event(
        session,
        flow_id=result.request.flow_id,
        organization_id=organization_id,
        module_name=result.request.module_name,
        event_type="ai.result.applied",
        request_id=result.request_id,
        user_id=user_id,
        data=application,
    )
    await session.flush()
    return result


async def usage_summary(session: AsyncSession, organization_id: UUID) -> dict[str, Any]:
    requests = list(
        (
            await session.scalars(
                select(AIGenerationRequest).where(AIGenerationRequest.organization_id == organization_id)
            )
        ).all()
    )
    usage = list(
        (
            await session.scalars(
                select(AIUsageRecord).where(AIUsageRecord.organization_id == organization_id)
            )
        ).all()
    )
    by_module: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"requests": 0, "completed": 0, "failed": 0, "cost": 0.0}
    )
    request_by_id = {row.id: row for row in requests}
    for row in requests:
        bucket = by_module[row.module_name]
        bucket["requests"] = int(bucket["requests"]) + 1
        if row.status == "completed":
            bucket["completed"] = int(bucket["completed"]) + 1
        if row.status == "failed":
            bucket["failed"] = int(bucket["failed"]) + 1
    for row in usage:
        request = request_by_id.get(row.request_id)
        if request:
            bucket = by_module[request.module_name]
            bucket["cost"] = round(float(bucket["cost"]) + row.estimated_cost, 8)
    return {
        "request_count": len(requests),
        "completed_count": sum(1 for row in requests if row.status == "completed"),
        "failed_count": sum(1 for row in requests if row.status == "failed"),
        "input_units": sum(row.input_units for row in usage),
        "output_units": sum(row.output_units for row in usage),
        "image_count": sum(row.image_count for row in usage),
        "estimated_cost": round(sum(row.estimated_cost for row in usage), 8),
        "by_module": dict(by_module),
    }
