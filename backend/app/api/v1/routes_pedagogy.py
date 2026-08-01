from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db_session
from app.models.auth import Membership, OrganizationRole, User
from app.models.document import Document, DocumentChapter
from app.models.education import Project, Subject
from app.models.pedagogy import (
    ComputationalThinkingPillar,
    GenerationProject,
    GenerationProjectPillar,
    GenerationSource,
    GenerationStatus,
    LearningUnit,
    PillarRelevance,
    PrivacyLevel,
)
from app.schemas.pedagogy import (
    CatalogResponse,
    GenerationPillarRead,
    GenerationProjectCreate,
    GenerationProjectRead,
    GenerationProjectUpdate,
    GenerationSourceInput,
    GenerationSourceRead,
    LearningUnitCreate,
    LearningUnitRead,
    LearningUnitUpdate,
    MockProposalResponse,
    PillarRead,
    PillarRecommendation,
    PillarRecommendationRequest,
)

router = APIRouter(tags=["Planejamento pedagógico"])

READ_ROLES = (
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.TEACHER,
    OrganizationRole.MEMBER,
)
WRITE_ROLES = (
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.TEACHER,
)

MATERIAL_TYPES = [
    "comic",
    "quiz",
    "activity",
    "educational_game",
    "crossword",
    "word_search",
    "anime_script",
    "storyboard",
    "lesson_plan",
]
ACCESSIBILITY_OPTIONS = [
    "alt_text",
    "large_font",
    "high_contrast",
    "black_and_white",
    "simplified_language",
    "audio_description",
    "captions",
    "screen_reader",
    "dyslexia_friendly",
    "bilingual",
]
STANDARD_SUBJECT_CODES = [
    "LP",
    "ARTE",
    "EF",
    "ING",
    "MAT",
    "CIE",
    "GEO",
    "HIS",
    "ER",
    "BIO",
    "FIS",
    "QUI",
    "FIL",
    "SOC",
    "LIT",
    "RED",
    "PC",
]
ASSESSMENT_DESIGNS = [
    "none",
    "diagnostic",
    "pre_post",
    "experimental_control",
    "formative",
    "summative",
    "tam",
]


def organization_id(membership: Membership) -> UUID:
    return membership.organization_id


async def validate_subject(
    subject_id: UUID | None,
    membership: Membership,
    session: AsyncSession,
) -> None:
    if subject_id is None:
        return
    subject = await session.scalar(
        select(Subject).where(
            Subject.id == subject_id,
            Subject.organization_id == organization_id(membership),
        )
    )
    if subject is None:
        raise HTTPException(status_code=404, detail="Disciplina não encontrada")


async def validate_project(
    project_id: UUID | None,
    membership: Membership,
    session: AsyncSession,
) -> None:
    if project_id is None:
        return
    project = await session.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.organization_id == organization_id(membership),
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto educacional não encontrado")


async def validate_chapter(
    chapter_id: UUID | None,
    membership: Membership,
    session: AsyncSession,
) -> DocumentChapter | None:
    if chapter_id is None:
        return None
    chapter = await session.scalar(
        select(DocumentChapter)
        .join(Document, Document.id == DocumentChapter.document_id)
        .where(
            DocumentChapter.id == chapter_id,
            Document.organization_id == organization_id(membership),
        )
    )
    if chapter is None:
        raise HTTPException(status_code=404, detail="Capítulo não encontrado")
    return chapter


async def validate_generation_sources(
    sources: list[GenerationSourceInput],
    membership: Membership,
    session: AsyncSession,
) -> None:
    org_id = organization_id(membership)
    for source in sources:
        if source.document_id is not None:
            document = await session.scalar(
                select(Document).where(
                    Document.id == source.document_id,
                    Document.organization_id == org_id,
                )
            )
            if document is None:
                raise HTTPException(status_code=404, detail="Documento da fonte não encontrado")
        if source.chapter_id is not None:
            await validate_chapter(source.chapter_id, membership, session)
        if source.learning_unit_id is not None:
            unit = await session.scalar(
                select(LearningUnit).where(
                    LearningUnit.id == source.learning_unit_id,
                    LearningUnit.organization_id == org_id,
                )
            )
            if unit is None:
                raise HTTPException(
                    status_code=404, detail="Unidade pedagógica da fonte não encontrada"
                )


async def validate_pillars(
    pillar_ids: list[UUID],
    session: AsyncSession,
) -> dict[UUID, ComputationalThinkingPillar]:
    if not pillar_ids:
        return {}
    result = await session.scalars(
        select(ComputationalThinkingPillar).where(
            ComputationalThinkingPillar.id.in_(pillar_ids),
            ComputationalThinkingPillar.is_active.is_(True),
        )
    )
    pillars = {pillar.id: pillar for pillar in result.all()}
    if len(pillars) != len(set(pillar_ids)):
        raise HTTPException(status_code=400, detail="Um ou mais pilares são inválidos")
    return pillars


async def get_generation_project(
    generation_project_id: UUID,
    membership: Membership,
    session: AsyncSession,
) -> GenerationProject:
    conditions = [
        GenerationProject.id == generation_project_id,
        GenerationProject.organization_id == organization_id(membership),
    ]
    if membership.role not in (OrganizationRole.OWNER, OrganizationRole.ADMIN):
        conditions.append(
            or_(
                GenerationProject.privacy_level != PrivacyLevel.PRIVATE,
                GenerationProject.created_by_user_id == membership.user_id,
            )
        )
    project = await session.scalar(
        select(GenerationProject)
        .where(*conditions)
        .options(
            selectinload(GenerationProject.pillars).selectinload(GenerationProjectPillar.pillar),
            selectinload(GenerationProject.sources),
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto de geração não encontrado")
    return project


def ensure_can_modify_generation_project(
    project: GenerationProject,
    membership: Membership,
) -> None:
    if membership.role in (OrganizationRole.OWNER, OrganizationRole.ADMIN):
        return
    if project.created_by_user_id != membership.user_id:
        raise HTTPException(
            status_code=403,
            detail="Apenas o autor ou um administrador pode alterar este projeto",
        )


def serialize_generation_project(project: GenerationProject) -> GenerationProjectRead:
    return GenerationProjectRead(
        id=project.id,
        organization_id=project.organization_id,
        project_id=project.project_id,
        created_by_user_id=project.created_by_user_id,
        created_by_name_snapshot=project.created_by_name_snapshot,
        title=project.title,
        source_mode=project.source_mode,
        subject_id=project.subject_id,
        custom_subject_name=project.custom_subject_name,
        school_year=project.school_year,
        topic=project.topic,
        disciplinary_objective=project.disciplinary_objective,
        computational_thinking_objective=project.computational_thinking_objective,
        teacher_text=project.teacher_text,
        teacher_instructions=project.teacher_instructions,
        allow_ai_expansion=project.allow_ai_expansion,
        fidelity_level=project.fidelity_level,
        integration_mode=project.integration_mode,
        difficulty_level=project.difficulty_level,
        privacy_level=project.privacy_level,
        credit_name=project.credit_name,
        rights_confirmed=project.rights_confirmed,
        bncc_skills=project.bncc_skills,
        desired_materials=project.desired_materials,
        accessibility_options=project.accessibility_options,
        source_priority=project.source_priority,
        assessment_design=project.assessment_design,
        assessment_notes=project.assessment_notes,
        cognitive_levels=project.cognitive_levels,
        measurable_objectives=project.measurable_objectives,
        evaluation_plan=project.evaluation_plan,
        author_credit_settings=project.author_credit_settings,
        status=project.status,
        pillars=[
            GenerationPillarRead(
                id=item.id,
                pillar_id=item.pillar_id,
                code=item.pillar.code,
                name=item.pillar.name,
                relevance=item.relevance,
                application_description=item.application_description,
                selected_by=item.selected_by,
            )
            for item in project.pillars
        ],
        sources=[
            GenerationSourceRead(
                id=source.id,
                source_type=source.source_type,
                document_id=source.document_id,
                chapter_id=source.chapter_id,
                learning_unit_id=source.learning_unit_id,
                content_text=source.content_text,
                instructions=source.instructions,
                priority=source.priority,
                weight=source.weight,
                is_primary=source.is_primary,
                allow_ai_expansion=source.allow_ai_expansion,
            )
            for source in sorted(project.sources, key=lambda item: item.priority)
        ],
        mock_proposal=project.mock_proposal,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


async def replace_pillars_and_sources(
    project: GenerationProject,
    data: GenerationProjectCreate | GenerationProjectUpdate,
    session: AsyncSession,
) -> None:
    if data.pillars is not None:
        await validate_pillars([item.pillar_id for item in data.pillars], session)
        await session.execute(
            delete(GenerationProjectPillar).where(
                GenerationProjectPillar.generation_project_id == project.id
            )
        )
        for item in data.pillars:
            session.add(
                GenerationProjectPillar(
                    generation_project_id=project.id,
                    pillar_id=item.pillar_id,
                    relevance=item.relevance,
                    application_description=item.application_description,
                    selected_by="teacher",
                )
            )
    if data.sources is not None:
        await session.execute(
            delete(GenerationSource).where(GenerationSource.generation_project_id == project.id)
        )
        for source_item in data.sources:
            session.add(
                GenerationSource(
                    generation_project_id=project.id,
                    **source_item.model_dump(),
                )
            )


@router.get("/pedagogy/catalog", response_model=CatalogResponse)
async def pedagogy_catalog(
    session: AsyncSession = Depends(get_db_session),
    _: Membership = Depends(require_roles(*READ_ROLES)),
) -> CatalogResponse:
    pillars = list(
        (
            await session.scalars(
                select(ComputationalThinkingPillar)
                .where(ComputationalThinkingPillar.is_active.is_(True))
                .order_by(ComputationalThinkingPillar.name)
            )
        ).all()
    )
    return CatalogResponse(
        pillars=[PillarRead.model_validate(pillar) for pillar in pillars],
        standard_subject_codes=STANDARD_SUBJECT_CODES,
        material_types=MATERIAL_TYPES,
        accessibility_options=ACCESSIBILITY_OPTIONS,
        assessment_designs=ASSESSMENT_DESIGNS,
    )


@router.post("/pedagogy/recommend-pillars", response_model=list[PillarRecommendation])
async def recommend_pillars(
    data: PillarRecommendationRequest,
    session: AsyncSession = Depends(get_db_session),
    _: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[PillarRecommendation]:
    pillars = list(
        (
            await session.scalars(
                select(ComputationalThinkingPillar).where(
                    ComputationalThinkingPillar.is_active.is_(True)
                )
            )
        ).all()
    )
    by_code = {pillar.code: pillar for pillar in pillars}
    text = f"{data.subject_name} {data.topic}".lower()

    priorities: list[tuple[str, PillarRelevance, str]]
    if any(word in text for word in ("matem", "fraç", "geometr", "física", "química")):
        priorities = [
            (
                "pattern_recognition",
                PillarRelevance.HIGH,
                "Identificar regularidades e relações no conteúdo.",
            ),
            (
                "abstraction",
                PillarRelevance.HIGH,
                "Selecionar dados essenciais e representar o problema.",
            ),
            (
                "algorithms",
                PillarRelevance.MEDIUM,
                "Organizar procedimentos e sequências de resolução.",
            ),
            (
                "decomposition",
                PillarRelevance.COMPLEMENTARY,
                "Dividir problemas complexos em partes menores.",
            ),
        ]
    elif any(word in text for word in ("ciên", "biolog", "ecoss", "sistema", "geograf")):
        priorities = [
            (
                "decomposition",
                PillarRelevance.HIGH,
                "Analisar sistemas por componentes e relações.",
            ),
            (
                "pattern_recognition",
                PillarRelevance.HIGH,
                "Comparar fenômenos e identificar regularidades.",
            ),
            ("abstraction", PillarRelevance.MEDIUM, "Construir modelos simplificados do fenômeno."),
            (
                "algorithms",
                PillarRelevance.COMPLEMENTARY,
                "Organizar etapas de investigação ou classificação.",
            ),
        ]
    else:
        priorities = [
            (
                "abstraction",
                PillarRelevance.HIGH,
                "Distinguir ideias centrais de detalhes secundários.",
            ),
            (
                "decomposition",
                PillarRelevance.MEDIUM,
                "Dividir textos, processos ou eventos em partes.",
            ),
            (
                "pattern_recognition",
                PillarRelevance.MEDIUM,
                "Comparar estruturas, estilos ou acontecimentos.",
            ),
            (
                "algorithms",
                PillarRelevance.COMPLEMENTARY,
                "Organizar etapas para produzir ou analisar conteúdos.",
            ),
        ]

    return [
        PillarRecommendation(
            pillar_id=by_code[code].id,
            code=code,
            name=by_code[code].name,
            relevance=relevance,
            justification=justification,
        )
        for code, relevance, justification in priorities
        if code in by_code
    ]


@router.get("/learning-units", response_model=list[LearningUnitRead])
async def list_learning_units(
    chapter_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[LearningUnit]:
    query = select(LearningUnit).where(LearningUnit.organization_id == organization_id(membership))
    if chapter_id is not None:
        query = query.where(LearningUnit.chapter_id == chapter_id)
    result = await session.scalars(query.order_by(LearningUnit.position, LearningUnit.title))
    return list(result.all())


@router.post("/learning-units", response_model=LearningUnitRead, status_code=201)
async def create_learning_unit(
    data: LearningUnitCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> LearningUnit:
    chapter = await validate_chapter(data.chapter_id, membership, session)
    await validate_subject(data.subject_id, membership, session)
    if chapter is not None:
        if data.start_page is not None and data.start_page < chapter.start_page:
            raise HTTPException(status_code=400, detail="A unidade começa antes do capítulo")
        if data.end_page is not None and data.end_page > chapter.end_page:
            raise HTTPException(status_code=400, detail="A unidade termina depois do capítulo")
    unit = LearningUnit(
        organization_id=organization_id(membership),
        **data.model_dump(),
    )
    session.add(unit)
    await session.commit()
    await session.refresh(unit)
    return unit


@router.patch("/learning-units/{unit_id}", response_model=LearningUnitRead)
async def update_learning_unit(
    unit_id: UUID,
    data: LearningUnitUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> LearningUnit:
    unit = await session.scalar(
        select(LearningUnit).where(
            LearningUnit.id == unit_id,
            LearningUnit.organization_id == organization_id(membership),
        )
    )
    if unit is None:
        raise HTTPException(status_code=404, detail="Unidade pedagógica não encontrada")
    values = data.model_dump(exclude_unset=True)
    if "subject_id" in values:
        await validate_subject(values["subject_id"], membership, session)
    start_page = values.get("start_page", unit.start_page)
    end_page = values.get("end_page", unit.end_page)
    if start_page is not None and end_page is not None and end_page < start_page:
        raise HTTPException(status_code=400, detail="Intervalo de páginas inválido")
    for field, value in values.items():
        setattr(unit, field, value)
    await session.commit()
    await session.refresh(unit)
    return unit


@router.delete("/learning-units/{unit_id}", status_code=204)
async def delete_learning_unit(
    unit_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Response:
    unit = await session.scalar(
        select(LearningUnit).where(
            LearningUnit.id == unit_id,
            LearningUnit.organization_id == organization_id(membership),
        )
    )
    if unit is None:
        raise HTTPException(status_code=404, detail="Unidade pedagógica não encontrada")
    await session.delete(unit)
    await session.commit()
    return Response(status_code=204)


@router.get("/generation-projects", response_model=list[GenerationProjectRead])
async def list_generation_projects(
    status: GenerationStatus | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[GenerationProjectRead]:
    query = (
        select(GenerationProject)
        .where(GenerationProject.organization_id == organization_id(membership))
        .options(
            selectinload(GenerationProject.pillars).selectinload(GenerationProjectPillar.pillar),
            selectinload(GenerationProject.sources),
        )
        .order_by(GenerationProject.updated_at.desc())
    )
    if membership.role not in (OrganizationRole.OWNER, OrganizationRole.ADMIN):
        query = query.where(
            or_(
                GenerationProject.privacy_level != PrivacyLevel.PRIVATE,
                GenerationProject.created_by_user_id == membership.user_id,
            )
        )
    if status is not None:
        query = query.where(GenerationProject.status == status)
    projects = list((await session.scalars(query)).all())
    return [serialize_generation_project(project) for project in projects]


@router.post("/generation-projects", response_model=GenerationProjectRead, status_code=201)
async def create_generation_project(
    data: GenerationProjectCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    current_user: User = Depends(get_current_user),
) -> GenerationProjectRead:
    await validate_subject(data.subject_id, membership, session)
    await validate_project(data.project_id, membership, session)
    await validate_generation_sources(data.sources, membership, session)
    await validate_pillars([item.pillar_id for item in data.pillars], session)

    values = data.model_dump(exclude={"pillars", "sources", "credit_name"})
    project = GenerationProject(
        organization_id=organization_id(membership),
        created_by_user_id=current_user.id,
        created_by_name_snapshot=current_user.full_name,
        credit_name=(data.credit_name or current_user.full_name).strip(),
        **values,
    )
    session.add(project)
    await session.flush()
    await replace_pillars_and_sources(project, data, session)
    await session.commit()
    return serialize_generation_project(
        await get_generation_project(project.id, membership, session)
    )


@router.get("/generation-projects/{generation_project_id}", response_model=GenerationProjectRead)
async def read_generation_project(
    generation_project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> GenerationProjectRead:
    project = await get_generation_project(generation_project_id, membership, session)
    return serialize_generation_project(project)


@router.patch(
    "/generation-projects/{generation_project_id}",
    response_model=GenerationProjectRead,
)
async def update_generation_project(
    generation_project_id: UUID,
    data: GenerationProjectUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> GenerationProjectRead:
    project = await get_generation_project(generation_project_id, membership, session)
    ensure_can_modify_generation_project(project, membership)
    values = data.model_dump(exclude_unset=True, exclude={"pillars", "sources"})
    if "subject_id" in values:
        await validate_subject(values["subject_id"], membership, session)
    if "project_id" in values:
        await validate_project(values["project_id"], membership, session)
    if data.sources is not None:
        await validate_generation_sources(data.sources, membership, session)
    for field, value in values.items():
        setattr(project, field, value)
    await replace_pillars_and_sources(project, data, session)
    await session.commit()
    return serialize_generation_project(
        await get_generation_project(project.id, membership, session)
    )


@router.delete("/generation-projects/{generation_project_id}", status_code=204)
async def delete_generation_project(
    generation_project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Response:
    project = await get_generation_project(generation_project_id, membership, session)
    ensure_can_modify_generation_project(project, membership)
    await session.delete(project)
    await session.commit()
    return Response(status_code=204)


@router.post(
    "/generation-projects/{generation_project_id}/mock-proposal",
    response_model=MockProposalResponse,
)
async def create_mock_proposal(
    generation_project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> MockProposalResponse:
    project = await get_generation_project(generation_project_id, membership, session)
    ensure_can_modify_generation_project(project, membership)
    source_labels = [
        {
            "type": source.source_type.value,
            "document_id": str(source.document_id) if source.document_id else None,
            "chapter_id": str(source.chapter_id) if source.chapter_id else None,
            "learning_unit_id": str(source.learning_unit_id) if source.learning_unit_id else None,
            "priority": source.priority,
        }
        for source in sorted(project.sources, key=lambda item: item.priority)
    ]
    proposal: dict[str, object] = {
        "provider": "mock",
        "title": project.title,
        "topic": project.topic,
        "author_credit": project.credit_name,
        "source_mode": project.source_mode.value,
        "source_hierarchy": source_labels,
        "disciplinary_objective": project.disciplinary_objective,
        "computational_thinking_objective": project.computational_thinking_objective,
        "pillars": [
            {
                "code": link.pillar.code,
                "name": link.pillar.name,
                "application": link.application_description
                or f"Aplicar {link.pillar.name.lower()} ao tema {project.topic}.",
            }
            for link in project.pillars
        ],
        "materials": [
            {
                "type": material,
                "status": "planned",
                "mock_summary": (
                    f"[MOCK] {material} sobre {project.topic}, integrado aos pilares "
                    + ", ".join(link.pillar.name for link in project.pillars)
                    + "."
                ),
            }
            for material in project.desired_materials
        ],
        "bncc_skills": project.bncc_skills,
        "accessibility": project.accessibility_options,
        "cognitive_levels": project.cognitive_levels,
        "measurable_objectives": project.measurable_objectives,
        "author_credit_settings": project.author_credit_settings,
        "assessment": {
            "design": project.assessment_design.value,
            "notes": project.assessment_notes,
            "plan": project.evaluation_plan,
            "future_metrics": [
                "desempenho disciplinar",
                "desempenho por pilar de PC",
                "análise por item",
                "comparação pré/pós quando aplicável",
            ],
        },
        "traceability": {
            "created_by": project.created_by_name_snapshot,
            "rights_confirmed": project.rights_confirmed,
            "privacy": project.privacy_level.value,
        },
    }
    project.mock_proposal = proposal
    project.status = GenerationStatus.IN_REVIEW
    await session.commit()
    return MockProposalResponse(
        generation_project_id=project.id,
        proposal=proposal,
    )
