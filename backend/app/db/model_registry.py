"""Registro unico de modelos SQLAlchemy.

Este modulo deve ser importado pelo Alembic e pelo diagnostico da aplicacao para
garantir que a metadata conheca tanto o nucleo original quanto os modulos
incrementais das Sprints 14.1 a 16.9.
"""

from app import models as core_models  # noqa: F401
from app.adaptive_evolution import models as adaptive_evolution_models  # noqa: F401
from app.adaptive_insights import models as adaptive_insights_models  # noqa: F401
from app.anime_studio import models as anime_studio_models  # noqa: F401
from app.assessment_analytics import models as assessment_analytics_models  # noqa: F401
from app.assessment_delivery import models as assessment_delivery_models  # noqa: F401
from app.assessment_hub import models as assessment_hub_models  # noqa: F401
from app.assessment_review import models as assessment_review_models  # noqa: F401
from app.comic_layout_studio import models as comic_layout_studio_models  # noqa: F401
from app.comic_page_editor import models as comic_page_editor_models  # noqa: F401
from app.comic_reader_access import models as comic_reader_access_models  # noqa: F401
from app.comic_reader_analytics import models as comic_reader_analytics_models  # noqa: F401
from app.comic_review_publish import models as comic_review_publish_models  # noqa: F401
from app.comic_visual_library import models as comic_visual_library_models  # noqa: F401
from app.db.base import Base
from app.institutional_governance import models as institutional_governance_models  # noqa: F401
from app.instrument_governance import models as instrument_governance_models  # noqa: F401
from app.intervention_effectiveness import models as intervention_effectiveness_models  # noqa: F401
from app.intervention_orchestration import (
    __version__ as intervention_orchestration_version,  # noqa: F401
)
from app.school_admissions import models as school_admissions_models  # noqa: F401
from app.student_portfolio import models as student_portfolio_models  # noqa: F401


def registered_table_names() -> tuple[str, ...]:
    return tuple(sorted(Base.metadata.tables))


EXPECTED_INCREMENTAL_PREFIXES = (
    "adaptive_",
    "assessment_hub_",
    "assessment_delivery_",
    "instrument_",
    "anime_",
    "student_portfolio_",
    "school_",
    "student_enrollment_",
    "guardian_",
    "seat_",
    "enrollment_waitlist",
    "enrollment_document_",
    "enrollment_contract_",
    "class_capacity",
    "institutional_staff_",
    "assessment_review_",
    "assessment_analytics_",
    "hq_",
    "comic_visual_",
    "comic_editorial_",
    "comic_reader_",
    "comic_reading_",
    "comic_narration_",
    "comic_glossary_",
    "comic_presentation_",
    "comic_embedded_",
)
