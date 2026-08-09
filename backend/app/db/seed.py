import asyncio

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.auth import Membership, Organization, OrganizationRole, User
from app.models.creative import CreativeItem, CreativeItemKind, CreativeStatus, CreativeVisibility
from app.models.education import Subject
from app.models.observability import OperationalAlertRule, OrganizationQuota, SLODefinition
from app.models.pedagogy import ComputationalThinkingPillar
from app.models.platform import DataRetentionPolicy, DeploymentRelease, FeatureFlag

CORE_SUBJECTS = [
    ("LP", "Língua Portuguesa", "Linguagens"),
    ("ARTE", "Arte", "Linguagens"),
    ("EF", "Educação Física", "Linguagens"),
    ("ING", "Língua Inglesa", "Linguagens"),
    ("MAT", "Matemática", "Matemática"),
    ("CIE", "Ciências", "Ciências da Natureza"),
    ("GEO", "Geografia", "Ciências Humanas"),
    ("HIS", "História", "Ciências Humanas"),
    ("ER", "Ensino Religioso", "Ensino Religioso"),
    ("BIO", "Biologia", "Ciências da Natureza"),
    ("FIS", "Física", "Ciências da Natureza"),
    ("QUI", "Química", "Ciências da Natureza"),
    ("FIL", "Filosofia", "Ciências Humanas"),
    ("SOC", "Sociologia", "Ciências Humanas"),
    ("LIT", "Literatura", "Linguagens"),
    ("RED", "Redação", "Linguagens"),
    (
        "PC",
        "Pensamento Computacional",
        "Computação transversal integrada às disciplinas",
    ),
]

PILLARS = [
    (
        "abstraction",
        "Abstração",
        (
            "Selecionar informações essenciais, ignorar detalhes irrelevantes e "
            "construir representações úteis."
        ),
        (
            "Ideia principal de um texto; variáveis relevantes de um problema; "
            "mapas, modelos e sínteses."
        ),
    ),
    (
        "decomposition",
        "Decomposição",
        "Dividir problemas, sistemas ou tarefas complexas em partes menores e administráveis.",
        (
            "Separar um ecossistema em componentes; dividir uma narrativa em cenas; "
            "decompor um cálculo."
        ),
    ),
    (
        "pattern_recognition",
        "Reconhecimento de padrões",
        "Identificar regularidades, semelhanças, diferenças e relações reutilizáveis.",
        "Frações equivalentes; padrões climáticos; estruturas textuais; sequências históricas.",
    ),
    (
        "algorithms",
        "Algoritmos",
        (
            "Criar, executar, testar e aperfeiçoar sequências ordenadas de passos "
            "para alcançar um objetivo."
        ),
        (
            "Procedimentos matemáticos; protocolos científicos; linhas do tempo; "
            "instruções e coreografias."
        ),
    ),
]

STARTER_CREATIVE_ITEMS: list[tuple[CreativeItemKind, str, str, dict[str, object]]] = [
    (
        CreativeItemKind.CHARACTER,
        "Professor Byte",
        "Mediador pedagógico do EduCode que orienta sem entregar a resposta.",
        {
            "age_range": "adulto",
            "physical_description": "Professor acolhedor com elementos visuais tecnológicos.",
            "personality": "curioso, paciente e questionador",
            "speaking_style": "linguagem clara e perguntas orientadoras",
            "pedagogical_role": "mediador",
            "mandatory_features": ["não resolver o desafio diretamente"],
            "prohibited_features": ["linguagem inadequada à faixa etária"],
        },
    ),
    (
        CreativeItemKind.SCENE,
        "Sala de aula contemporânea",
        "Ambiente escolar acolhedor, inclusivo e preparado para atividades colaborativas.",
        {
            "setting_type": "sala de aula",
            "period": "contemporâneo",
            "atmosphere": "acolhedora e colaborativa",
            "pedagogical_use": "explicações, desafios e trabalho em grupo",
            "mandatory_elements": ["quadro", "mesas", "espaço acessível"],
        },
    ),
    (
        CreativeItemKind.STYLE,
        "Anime educativo",
        "Visual expressivo, colorido e apropriado para materiais pedagógicos.",
        {
            "style_category": "anime educativo",
            "visual_language": "traço limpo, expressões claras e cenários legíveis",
            "narrative_tone": "aventura leve",
            "pedagogical_tone": "investigativo",
            "recommended_age_group": "anos iniciais ao ensino médio",
        },
    ),
    (
        CreativeItemKind.STYLE,
        "Cartoon escolar",
        "Estilo lúdico, simples e colorido para materiais dos anos iniciais.",
        {
            "style_category": "cartoon",
            "visual_language": "formas simples, alto contraste e leitura rápida",
            "narrative_tone": "humorístico e acolhedor",
            "pedagogical_tone": "explicativo",
            "recommended_age_group": "educação infantil e anos iniciais",
        },
    ),
    (
        CreativeItemKind.STYLE,
        "Storyboard didático",
        "Representação visual econômica para planejar HQs, vídeos e animes.",
        {
            "style_category": "storyboard",
            "visual_language": "quadros funcionais, anotações de câmera e ações",
            "narrative_tone": "objetivo",
            "pedagogical_tone": "planejamento",
            "recommended_age_group": "todas",
        },
    ),
]

DEFAULT_FEATURE_FLAGS = [
    ("ai.real_provider", False, "Libera provedores reais após homologação."),
    ("assessment.external_connectors", False, "Libera conectores QTI, LTI, xAPI e SCORM."),
    ("statistics.advanced", True, "Mantém o laboratório estatístico avançado disponível."),
    ("platform.pilot_mode", True, "Identifica a organização como ambiente piloto."),
    ("SCHOOL_ADMISSIONS_ENABLED", False, "Libera matrículas e controle de vagas."),
    ("SCHOOL_SECRETARIAT_ENABLED", False, "Libera a Secretaria Digital."),
    ("SCHOOL_REPORT_CARDS_ENABLED", False, "Libera boletins escolares."),
    ("SCHOOL_EVENTS_ENABLED", False, "Libera eventos e passeios escolares."),
    ("SCHOOL_ANNOUNCEMENTS_ENABLED", False, "Libera comunicados institucionais."),
    ("SCHOOL_FINANCE_ENABLED", False, "Libera o financeiro escolar separado."),
    ("FAMILY_PORTAL_ENABLED", False, "Libera o Portal da Família."),
]

DEFAULT_SLOS = [
    (
        "backend_availability",
        "Disponibilidade do backend",
        "http.error_rate_percent",
        "<=",
        0.5,
        60,
    ),
    ("http_latency_p95", "Latência HTTP p95", "http.latency_p95_ms", "<=", 500.0, 60),
    ("job_success_rate", "Taxa de falha das tarefas", "jobs.failure_rate_percent", "<=", 2.0, 1440),
    ("workers_available", "Workers ativos", "workers.active", ">=", 4.0, 15),
]

DEFAULT_ALERT_RULES = [
    (
        "http_errors_high",
        "Taxa elevada de erros HTTP",
        "http.error_rate_percent",
        ">",
        2.0,
        "critical",
    ),
    (
        "http_latency_high",
        "Latência HTTP acima da meta",
        "http.latency_p95_ms",
        ">",
        1000.0,
        "warning",
    ),
    ("jobs_failed", "Falhas recentes de processamento", "jobs.failed_24h", ">", 3.0, "warning"),
    ("worker_shortage", "Workers insuficientes", "workers.active", "<", 4.0, "critical"),
    ("open_incidents", "Incidentes operacionais abertos", "incidents.open", ">", 0.0, "warning"),
]

DEFAULT_QUOTAS = [
    ("users.total", 500.0, "total", "warn"),
    ("projects.total", 1000.0, "total", "warn"),
    ("documents.total", 10000.0, "total", "warn"),
    ("assessments.total", 5000.0, "total", "warn"),
    ("jobs.active", 100.0, "instant", "block"),
    ("ai.cost.monthly", 1000.0, "monthly", "warn"),
]

DEFAULT_RETENTION_POLICIES = [
    ("technical_logs", 90, "Segurança e operação"),
    ("critical_audit", 1825, "Obrigação legal e proteção institucional"),
    ("anonymized_ai_prompts", 180, "Melhoria controlada do serviço"),
    ("temporary_files", 7, "Execução técnica temporária"),
    ("student_learning_records", 1825, "Execução da política educacional"),
]


async def ensure_bootstrap_principal(
    session: AsyncSession,
    settings: Settings,
) -> tuple[Organization, User]:
    """Create the initial principal without restoring revoked privileges."""
    organization = await session.scalar(
        select(Organization).where(Organization.slug == settings.initial_organization_slug)
    )
    if organization is None:
        organization = Organization(
            name=settings.initial_organization_name,
            slug=settings.initial_organization_slug,
            is_active=True,
        )
        session.add(organization)
        await session.flush()

    email = str(settings.initial_admin_email).strip().lower()
    user = await session.scalar(select(User).where(User.email == email))
    user_created = user is None
    if user_created:
        user = User(
            email=email,
            full_name=settings.initial_admin_name,
            hashed_password=hash_password(settings.initial_admin_password),
            is_active=True,
            is_superuser=True,
        )
        session.add(user)
        await session.flush()

    assert user is not None
    membership = await session.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == organization.id,
        )
    )
    if membership is None and user_created:
        session.add(
            Membership(
                user_id=user.id,
                organization_id=organization.id,
                role=OrganizationRole.OWNER,
                is_active=True,
            )
        )
    return organization, user


async def seed() -> None:
    settings = get_settings()

    async with AsyncSessionFactory() as session:
        organization, user = await ensure_bootstrap_principal(
            session,
            settings,
        )

        for code, name, area in CORE_SUBJECTS:
            subject = await session.scalar(
                select(Subject).where(
                    Subject.organization_id == organization.id,
                    Subject.code == code,
                )
            )
            description = (
                f"Componente curricular do catálogo inicial. Área: {area}. "
                "Pode ser integrado aos pilares do Pensamento Computacional."
            )
            if subject is None:
                session.add(
                    Subject(
                        organization_id=organization.id,
                        name=name,
                        code=code,
                        description=description,
                        is_active=True,
                    )
                )
            else:
                subject.name = name
                subject.description = description
                subject.is_active = True

        for code, name, description, examples in PILLARS:
            pillar = await session.scalar(
                select(ComputationalThinkingPillar).where(ComputationalThinkingPillar.code == code)
            )
            if pillar is None:
                session.add(
                    ComputationalThinkingPillar(
                        code=code,
                        name=name,
                        description=description,
                        pedagogical_examples=examples,
                        is_active=True,
                    )
                )
            else:
                pillar.name = name
                pillar.description = description
                pillar.pedagogical_examples = examples
                pillar.is_active = True

        for kind, name, description, profile_data in STARTER_CREATIVE_ITEMS:
            creative_item = await session.scalar(
                select(CreativeItem).where(
                    CreativeItem.organization_id == organization.id,
                    CreativeItem.kind == kind,
                    CreativeItem.name == name,
                )
            )
            if creative_item is None:
                session.add(
                    CreativeItem(
                        organization_id=organization.id,
                        created_by_user_id=user.id,
                        created_by_name_snapshot=user.full_name,
                        kind=kind,
                        name=name,
                        description=description,
                        profile_data=profile_data,
                        visibility=CreativeVisibility.ORGANIZATION,
                        status=CreativeStatus.ACTIVE,
                        rights_confirmed=True,
                        original_author="EduCode Enterprise",
                        license_notes="Modelo padrão interno do EduCode.",
                    )
                )
            else:
                creative_item.description = description
                creative_item.profile_data = profile_data
                creative_item.status = CreativeStatus.ACTIVE
                creative_item.visibility = CreativeVisibility.ORGANIZATION

        for flag_key, enabled, description in DEFAULT_FEATURE_FLAGS:
            flag = await session.scalar(
                select(FeatureFlag).where(
                    FeatureFlag.organization_id == organization.id,
                    FeatureFlag.flag_key == flag_key,
                    FeatureFlag.scope_type == "organization",
                    FeatureFlag.scope_id.is_(None),
                )
            )
            if flag is None:
                session.add(
                    FeatureFlag(
                        organization_id=organization.id,
                        flag_key=flag_key,
                        is_enabled=enabled,
                        scope_type="organization",
                        description=description,
                        updated_by_user_id=user.id,
                    )
                )

        for data_type, retention_days, legal_basis in DEFAULT_RETENTION_POLICIES:
            policy = await session.scalar(
                select(DataRetentionPolicy).where(
                    DataRetentionPolicy.organization_id == organization.id,
                    DataRetentionPolicy.data_type == data_type,
                )
            )
            if policy is None:
                session.add(
                    DataRetentionPolicy(
                        organization_id=organization.id,
                        data_type=data_type,
                        retention_days=retention_days,
                        delete_after_days=retention_days,
                        legal_basis=legal_basis,
                        created_by_user_id=user.id,
                        updated_by_user_id=user.id,
                    )
                )

        for slo_key, name, metric_name, comparator, target, window_minutes in DEFAULT_SLOS:
            slo = await session.scalar(
                select(SLODefinition).where(
                    SLODefinition.organization_id == organization.id,
                    SLODefinition.slo_key == slo_key,
                )
            )
            if slo is None:
                session.add(
                    SLODefinition(
                        organization_id=organization.id,
                        slo_key=slo_key,
                        name=name,
                        description="Meta operacional padrão da Sprint 13.1.",
                        metric_name=metric_name,
                        comparator=comparator,
                        target_value=target,
                        window_minutes=window_minutes,
                        minimum_samples=1,
                        severity="critical" if "workers" in slo_key else "warning",
                        created_by_user_id=user.id,
                        updated_by_user_id=user.id,
                    )
                )

        for rule_key, name, metric_name, comparator, threshold, severity in DEFAULT_ALERT_RULES:
            rule = await session.scalar(
                select(OperationalAlertRule).where(
                    OperationalAlertRule.organization_id == organization.id,
                    OperationalAlertRule.rule_key == rule_key,
                )
            )
            if rule is None:
                session.add(
                    OperationalAlertRule(
                        organization_id=organization.id,
                        rule_key=rule_key,
                        name=name,
                        metric_name=metric_name,
                        comparator=comparator,
                        threshold_value=threshold,
                        evaluation_window_minutes=5,
                        severity=severity,
                        cooldown_minutes=15,
                        description="Regra operacional padrão da Sprint 13.1.",
                        created_by_user_id=user.id,
                        updated_by_user_id=user.id,
                    )
                )

        for quota_key, limit_value, period, enforcement_mode in DEFAULT_QUOTAS:
            quota = await session.scalar(
                select(OrganizationQuota).where(
                    OrganizationQuota.organization_id == organization.id,
                    OrganizationQuota.quota_key == quota_key,
                )
            )
            if quota is None:
                session.add(
                    OrganizationQuota(
                        organization_id=organization.id,
                        quota_key=quota_key,
                        limit_value=limit_value,
                        period=period,
                        enforcement_mode=enforcement_mode,
                        warning_percentage=80.0,
                        critical_percentage=95.0,
                        updated_by_user_id=user.id,
                    )
                )

        migration_revision = await session.scalar(
            text("SELECT version_num FROM alembic_version LIMIT 1")
        )
        release = await session.scalar(
            select(DeploymentRelease).where(
                DeploymentRelease.organization_id == organization.id,
                DeploymentRelease.version == settings.app_version,
                DeploymentRelease.build_identifier == settings.build_identifier,
            )
        )
        if release is None:
            session.add(
                DeploymentRelease(
                    organization_id=organization.id,
                    version=settings.app_version,
                    build_identifier=settings.build_identifier,
                    commit_sha=settings.commit_sha,
                    environment=settings.environment,
                    migration_revision=str(migration_revision or "unknown"),
                    status="deployed",
                    release_notes=(f"Deploy automatizado do build {settings.build_identifier}."),
                    deployed_by_user_id=user.id,
                )
            )

        await session.commit()
        print(
            f"Seed concluído: {user.email} / {organization.slug} / "
            f"{len(CORE_SUBJECTS)} disciplinas / {len(PILLARS)} pilares / "
            f"{len(STARTER_CREATIVE_ITEMS)} itens criativos iniciais / Sprint 13.1 pronta"
        )


if __name__ == "__main__":
    asyncio.run(seed())
