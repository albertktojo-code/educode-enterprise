from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import get_settings
from app.db.alembic_autogenerate import process_revision_directives
from app.db.base import Base
from app.db import model_registry as _model_registry  # noqa: F401
from app.models.ai_runtime import (  # noqa: F401
    AIActivityEvent,
    AIGenerationRequest,
    AIGenerationResult,
    AIGenerationReview,
    AIModel,
    AIModuleLink,
    AIModulePolicy,
    AIPromptTemplate,
    AIProvider,
    AIUsageRecord,
)
from app.models.assessment import (  # noqa: F401
    Assessment,
    AssessmentAuditEvent,
    AssessmentConnector,
    AssessmentDeliveryLink,
    AssessmentImportJob,
    AssessmentOutcomeEvidence,
    AssessmentVersion,
    AssessmentVersionItem,
    QuestionBankItem,
)
from app.models.analytics import (  # noqa: F401
    AnalyticsRefreshJob,
    AssignmentItemMetric,
    ClassroomSkillMetric,
    LearningAlert,
    LearningIntervention,
    StudentProgressSnapshot,
    StudentSkillMetric,
)
from app.models.auth import (  # noqa: F401
    AuthSession,
    Membership,
    Organization,
    PasswordResetToken,
    User,
)
from app.models.comic import (  # noqa: F401
    ComicBalloon,
    ComicEditOperation,
    ComicGenerationRun,
    ComicPage,
    ComicPanel,
    ComicRegenerationProposal,
    ComicReviewApproval,
    ComicReviewComment,
    ComicVersion,
    GeneratedComic,
)
from app.models.creative import (  # noqa: F401
    CreativeAsset,
    CreativeBible,
    CreativeItem,
    CreativeVersion,
    GenerationProjectCreativeItem,
    TeachingSequence,
    TeachingSequenceItem,
)
from app.models.delivery import (  # noqa: F401
    AssignmentQuestion,
    AssignmentRecipient,
    LearningEvent,
    MaterialAssignment,
    StudentAnswer,
    StudentAttempt,
    UserNotification,
)
from app.models.document import Document, DocumentChapter, DocumentPage  # noqa: F401
from app.models.education import (  # noqa: F401
    Classroom,
    ClassroomEnrollment,
    ContentItem,
    Project,
    Subject,
)
from app.models.observability import (  # noqa: F401
    DataReconciliationRun,
    DiagnosticRun,
    OperationalAlertEvent,
    OperationalAlertRule,
    OperationalMetricSnapshot,
    OrganizationQuota,
    SLODefinition,
)
from app.models.operations import (  # noqa: F401
    BackgroundJob,
    BackgroundJobAttempt,
    BackgroundJobEvent,
    JobDependency,
    JobNotification,
    ProviderCircuitState,
    ResourceReservation,
    SemanticCacheEntry,
    WorkerHeartbeat,
)
from app.models.platform import (  # noqa: F401
    BackupRun,
    DataRetentionPolicy,
    DeploymentRelease,
    FeatureFlag,
    RestoreTest,
    SecurityEvent,
    ServiceHealthSnapshot,
    SystemAuditEvent,
    SystemIncident,
)
from app.models.pedagogy import (  # noqa: F401
    ComputationalThinkingPillar,
    GenerationProject,
    GenerationProjectPillar,
    GenerationSource,
    LearningUnit,
)
from app.models.rag import (  # noqa: F401
    RagContext,
    RagContextConflict,
    RagContextEvaluation,
    RagContextFact,
    RagContextRule,
    RagContextSource,
)
from app.models.retrieval import DocumentChunk, RetrievalFeedback, RetrievalIndexJob  # noqa: F401
from app.models.studio import (  # noqa: F401
    ArtDirectionPreset,
    PackageMaterial,
    PedagogicalPackage,
    PublicationPreparation,
    TeacherStudioDraft,
)
from app.models.statistics import (  # noqa: F401
    StatisticalAnalysis,
    StatisticalChart,
    StatisticalDataset,
    StatisticalReport,
    StatisticalStudy,
    StatisticalSensitivityRun,
    StatisticalMethodComparison,
    StatisticalReviewComment,
    StatisticalReportRevision,
    StatisticalSampleSizePlan,
)
from app.models.system_event import SystemEvent  # noqa: F401

config = context.config
settings = get_settings()
config.set_main_option("sqlalchemy.url", str(settings.database_url))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=str(settings.database_url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        process_revision_directives=process_revision_directives,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        process_revision_directives=process_revision_directives,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section)
    if configuration is None:
        raise RuntimeError("Configuração do Alembic não encontrada")

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
