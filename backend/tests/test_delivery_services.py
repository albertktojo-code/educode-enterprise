from datetime import UTC, datetime, timedelta

from app.models.delivery import (
    AnswerKeyPolicy,
    AssignmentQuestion,
    FeedbackPolicy,
    MaterialAssignment,
    QuestionType,
    StudentAttempt,
)
from app.models.studio import PedagogicalPackage
from app.services.delivery import (
    answer_key_available,
    grade_response,
    mock_question_inputs,
    normalize_text,
    results_available,
    student_material_snapshot,
)


def test_normalize_text_removes_accents_and_extra_spaces() -> None:
    assert normalize_text("  Aplicação   PRÁTICA ") == "aplicacao pratica"


def test_multiple_choice_grading_is_deterministic() -> None:
    outcome = grade_response(
        QuestionType.MULTIPLE_CHOICE,
        {"selected_option_id": "B"},
        {"correct_option_ids": ["B"]},
        2.5,
    )
    assert outcome.is_correct is True
    assert outcome.awarded_score == 2.5


def test_numeric_grading_respects_tolerance() -> None:
    accepted = grade_response(
        QuestionType.NUMERIC,
        {"value": "3,14"},
        {"value": 3.1415, "tolerance": 0.01},
        1,
    )
    rejected = grade_response(
        QuestionType.NUMERIC,
        {"value": 3.0},
        {"value": 3.1415, "tolerance": 0.01},
        1,
    )
    assert accepted.is_correct is True
    assert rejected.is_correct is False


def test_essay_is_never_automatically_graded() -> None:
    outcome = grade_response(QuestionType.ESSAY, {"text": "Minha análise"}, {}, 4)
    assert outcome.is_correct is None
    assert outcome.awarded_score == 0


def test_student_snapshot_hides_teacher_materials_and_answers() -> None:
    snapshot = {
        "teacher_materials": [{"type": "answer_key", "content": {"answers": ["A"]}}],
        "student_materials": [
            {
                "type": "quiz",
                "content": {"question_count": 5, "answer_key": {"correct": "A"}},
            }
        ],
    }
    safe = student_material_snapshot(snapshot)
    assert "teacher_materials" not in safe
    assert "answer_key" not in safe["student_materials"][0]["content"]
    assert safe["student_materials"][0]["content"]["question_count"] == 5


def test_mock_questions_include_objective_and_manual_item() -> None:
    package = PedagogicalPackage(
        title="Frações",
        shared_context={"topic": "frações equivalentes", "objective": "Reconhecer equivalências"},
    )
    questions = mock_question_inputs(package)
    assert len(questions) == 5
    assert any(
        item.question_type == QuestionType.ESSAY and item.manual_grading
        for item in questions
    )
    assert "frações equivalentes" in questions[0].prompt


def test_result_policy_after_submission() -> None:
    assignment = MaterialAssignment(
        maximum_score=10,
        feedback_policy=FeedbackPolicy.AFTER_SUBMISSION,
        answer_key_policy=AnswerKeyPolicy.AFTER_SUBMISSION,
    )
    attempt = StudentAttempt(assignment=assignment)
    now = datetime.now(UTC)
    assert results_available(assignment, attempt, now) is False
    assert answer_key_available(assignment, attempt, now) is False
    attempt.submitted_at = now
    assert results_available(assignment, attempt, now) is True
    assert answer_key_available(assignment, attempt, now) is True


def test_answer_key_after_due_date_does_not_leak_early() -> None:
    now = datetime.now(UTC)
    assignment = MaterialAssignment(
        maximum_score=10,
        feedback_policy=FeedbackPolicy.AFTER_DUE_DATE,
        answer_key_policy=AnswerKeyPolicy.AFTER_DUE_DATE,
        due_at=now + timedelta(hours=1),
    )
    attempt = StudentAttempt(assignment=assignment, submitted_at=now)
    assert answer_key_available(assignment, attempt, now) is False
    assert answer_key_available(assignment, attempt, now + timedelta(hours=2)) is True


def test_manual_question_keeps_answer_key_internal() -> None:
    question = AssignmentQuestion(
        position=1,
        question_type=QuestionType.ESSAY,
        prompt="Explique.",
        answer_key={"rubric": ["clareza", "aplicação"]},
        manual_grading=True,
    )
    assert question.manual_grading is True
    assert question.answer_key["rubric"] == ["clareza", "aplicação"]
