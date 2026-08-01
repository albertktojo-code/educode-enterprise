from uuid import uuid4

import pytest

from app.models.assessment import AssessmentDeliveryLink
from app.models.delivery import (
    AnswerKeyPolicy,
    AssignmentQuestion,
    AssignmentStatus,
    AssignmentType,
    FeedbackPolicy,
    MaterialAssignment,
    QuestionType,
)
from app.services.delivery import DeliveryError, duplicate_assignment


class DuplicateSession:
    def __init__(self, delivery_link: AssessmentDeliveryLink | None) -> None:
        self.delivery_link = delivery_link
        self.added: list[object] = []

    async def scalar(self, _statement):
        return self.delivery_link

    def add(self, entity: object) -> None:
        self.added.append(entity)

    async def flush(self) -> None:
        for entity in self.added:
            if isinstance(entity, (MaterialAssignment, AssessmentDeliveryLink)):
                if entity.id is None:
                    entity.id = uuid4()


@pytest.mark.asyncio
async def test_duplicate_assessment_preserves_canonical_traceability(monkeypatch) -> None:
    organization_id = uuid4()
    assessment_id = uuid4()
    assessment_version_id = uuid4()
    original = MaterialAssignment(
        id=uuid4(),
        organization_id=organization_id,
        package_id=None,
        assessment_version_id=assessment_version_id,
        created_by_user_id=uuid4(),
        created_by_name_snapshot="Professora",
        title="Avaliação diagnóstica",
        instructions="Responda com atenção.",
        assignment_type=AssignmentType.ASSESSMENT,
        status=AssignmentStatus.PUBLISHED,
        material_snapshot={"source": "integrated_assessment"},
        snapshot_version=3,
        time_limit_minutes=40,
        maximum_attempts=2,
        maximum_score=10,
        minimum_score=6,
        feedback_policy=FeedbackPolicy.AFTER_SUBMISSION,
        answer_key_policy=AnswerKeyPolicy.AFTER_DUE_DATE,
        randomize_questions=True,
        randomize_options=True,
        allow_pause=True,
        allow_late_submission=False,
        late_penalty_percent=0,
        show_result_immediately=False,
        settings={"assessment_checksum": "source-checksum"},
        questions=[
            AssignmentQuestion(
                package_material_id=None,
                question_bank_item_id=uuid4(),
                position=1,
                question_type=QuestionType.ESSAY,
                prompt="Explique a estratégia.",
                options=[],
                answer_key={"rubric": ["clareza"]},
                explanation="Resposta esperada.",
                points=4,
                difficulty="medium",
                curriculum_skill_codes=["EF06CO01"],
                ct_pillar_codes=["decomposition"],
                source_references=[
                    {"assessment_version_id": str(assessment_version_id)}
                ],
                manual_grading=True,
                shuffle_options=False,
                source_type="teacher",
                source_metadata={"reviewed": True},
                item_version=7,
                item_snapshot_checksum="item-checksum",
                is_annulled=False,
                annulment_reason=None,
            )
        ],
        recipients=[],
    )
    source_link = AssessmentDeliveryLink(
        id=uuid4(),
        organization_id=organization_id,
        assessment_id=assessment_id,
        assessment_version_id=assessment_version_id,
        material_assignment_id=original.id,
        created_by_user_id=original.created_by_user_id,
    )
    session = DuplicateSession(source_link)

    async def return_no_loaded_assignment(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        "app.services.delivery.get_assignment",
        return_no_loaded_assignment,
    )
    duplicating_user_id = uuid4()
    clone = await duplicate_assignment(
        session,
        assignment=original,
        user_id=duplicating_user_id,
        user_name="Professor revisor",
        title="Avaliação diagnóstica — nova aplicação",
        copy_recipients=False,
    )

    assert clone.package_id is None
    assert clone.assessment_version_id == assessment_version_id
    assert (
        clone.questions[0].question_bank_item_id
        == original.questions[0].question_bank_item_id
    )
    assert clone.questions[0].item_version == 7
    assert clone.questions[0].item_snapshot_checksum == "item-checksum"
    assert clone.questions[0].source_metadata == {"reviewed": True}

    cloned_link = next(
        entity for entity in session.added if isinstance(entity, AssessmentDeliveryLink)
    )
    assert cloned_link.assessment_id == assessment_id
    assert cloned_link.assessment_version_id == assessment_version_id
    assert cloned_link.material_assignment_id == clone.id
    assert cloned_link.created_by_user_id == duplicating_user_id


@pytest.mark.asyncio
async def test_duplicate_assessment_rejects_missing_delivery_link() -> None:
    assignment = MaterialAssignment(
        id=uuid4(),
        organization_id=uuid4(),
        package_id=None,
        assessment_version_id=uuid4(),
    )
    session = DuplicateSession(None)

    with pytest.raises(DeliveryError, match="vínculo canônico"):
        await duplicate_assignment(
            session,
            assignment=assignment,
            user_id=uuid4(),
            user_name="Professor",
            title=None,
            copy_recipients=False,
        )

    assert session.added == []
