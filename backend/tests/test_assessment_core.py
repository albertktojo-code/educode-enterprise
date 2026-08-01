from app.models.assessment import AssessmentSourceType, AssessmentStatus, QuestionBankStatus
from app.schemas.assessment import BankItemCreate, ImportJobCreate
from app.services.assessment import checksum
from app.models.delivery import QuestionType


def test_assessment_states_are_explicit() -> None:
    assert AssessmentStatus.DRAFT.value == "draft"
    assert AssessmentStatus.PUBLISHED.value == "published"
    assert AssessmentSourceType.AI.value == "ai"
    assert QuestionBankStatus.APPROVED.value == "approved"


def test_question_payload_supports_curriculum_and_ct() -> None:
    item = BankItemCreate(
        title="Decomposição",
        item_type=QuestionType.MULTIPLE_CHOICE,
        prompt="Qual etapa divide um problema em partes menores?",
        options=[{"id": "a", "text": "Decomposição"}, {"id": "b", "text": "Execução"}],
        answer_key={"correct_option_ids": ["a"]},
        curriculum_skill_codes=["EF06CO01"],
        ct_pillar_codes=["decomposition"],
    )
    assert item.curriculum_skill_codes == ["EF06CO01"]
    assert item.ct_pillar_codes == ["decomposition"]
    assert len(checksum(item.model_dump(mode="json"))) == 64


def test_import_formats_include_interoperability_standards() -> None:
    for source_format in ("csv", "xlsx", "json", "qti", "lti", "xapi", "scorm"):
        job = ImportJobCreate(source_format=source_format, rows=[])
        assert job.source_format == source_format
