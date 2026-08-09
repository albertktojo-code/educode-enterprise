from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.delivery import (
    AnswerKeyPolicy,
    AssignmentStatus,
    AssignmentType,
    AttemptStatus,
    FeedbackPolicy,
    NotificationStatus,
    QuestionType,
    RecipientStatus,
    RecipientType,
)


class RecipientInput(BaseModel):
    recipient_type: RecipientType
    classroom_id: UUID | None = None
    user_id: UUID | None = None
    available_from_override: datetime | None = None
    due_at_override: datetime | None = None
    maximum_attempts_override: int | None = Field(default=None, ge=1, le=20)
    time_limit_minutes_override: int | None = Field(default=None, ge=1, le=1440)
    accommodations: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_target(self) -> "RecipientInput":
        if self.recipient_type == RecipientType.CLASSROOM:
            if self.classroom_id is None or self.user_id is not None:
                raise ValueError("Destinatário de turma exige somente classroom_id")
        elif self.user_id is None or self.classroom_id is not None:
            raise ValueError("Destinatário individual exige somente user_id")
        return self


class QuestionInput(BaseModel):
    question_type: QuestionType
    prompt: str = Field(min_length=3, max_length=5000)
    options: list[dict[str, Any]] = Field(default_factory=list)
    answer_key: dict[str, Any] = Field(default_factory=dict)
    explanation: str = Field(default="", max_length=5000)
    points: float = Field(default=1.0, gt=0, le=1000)
    difficulty: str = Field(default="medium", max_length=40)
    curriculum_skill_codes: list[str] = Field(default_factory=list)
    ct_pillar_codes: list[str] = Field(default_factory=list)
    source_references: list[dict[str, Any]] = Field(default_factory=list)
    manual_grading: bool = False
    shuffle_options: bool = False


class AssignmentCreate(BaseModel):
    package_id: UUID
    title: str = Field(min_length=3, max_length=240)
    instructions: str = Field(default="", max_length=10000)
    assignment_type: AssignmentType = AssignmentType.READING_EXERCISE
    available_from: datetime | None = None
    due_at: datetime | None = None
    time_limit_minutes: int | None = Field(default=None, ge=1, le=1440)
    maximum_attempts: int = Field(default=1, ge=1, le=20)
    maximum_score: float = Field(default=10.0, gt=0, le=10000)
    minimum_score: float | None = Field(default=None, ge=0, le=10000)
    feedback_policy: FeedbackPolicy = FeedbackPolicy.AFTER_SUBMISSION
    answer_key_policy: AnswerKeyPolicy = AnswerKeyPolicy.AFTER_DUE_DATE
    randomize_questions: bool = False
    randomize_options: bool = False
    allow_pause: bool = True
    allow_late_submission: bool = False
    late_penalty_percent: float = Field(default=0.0, ge=0, le=100)
    show_result_immediately: bool = False
    settings: dict[str, Any] = Field(default_factory=dict)
    recipients: list[RecipientInput] = Field(default_factory=list)
    questions: list[QuestionInput] = Field(default_factory=list)
    generate_mock_questions: bool = True

    @model_validator(mode="after")
    def validate_dates_and_scores(self) -> "AssignmentCreate":
        if self.available_from and self.due_at and self.due_at <= self.available_from:
            raise ValueError("O prazo deve ser posterior à liberação")
        if self.minimum_score is not None and self.minimum_score > self.maximum_score:
            raise ValueError("A nota mínima não pode superar a nota máxima")
        return self


class AssignmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=240)
    instructions: str | None = Field(default=None, max_length=10000)
    assignment_type: AssignmentType | None = None
    available_from: datetime | None = None
    due_at: datetime | None = None
    time_limit_minutes: int | None = Field(default=None, ge=1, le=1440)
    maximum_attempts: int | None = Field(default=None, ge=1, le=20)
    maximum_score: float | None = Field(default=None, gt=0, le=10000)
    minimum_score: float | None = Field(default=None, ge=0, le=10000)
    feedback_policy: FeedbackPolicy | None = None
    answer_key_policy: AnswerKeyPolicy | None = None
    randomize_questions: bool | None = None
    randomize_options: bool | None = None
    allow_pause: bool | None = None
    allow_late_submission: bool | None = None
    late_penalty_percent: float | None = Field(default=None, ge=0, le=100)
    show_result_immediately: bool | None = None
    results_released_at: datetime | None = None
    settings: dict[str, Any] | None = None


class RecipientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recipient_type: RecipientType
    classroom_id: UUID | None
    user_id: UUID | None
    status: RecipientStatus
    available_from_override: datetime | None
    due_at_override: datetime | None
    maximum_attempts_override: int | None
    time_limit_minutes_override: int | None
    accommodations: dict[str, Any]
    assigned_at: datetime


class TeacherQuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    position: int
    question_type: QuestionType
    prompt: str
    options: list[dict[str, Any]]
    answer_key: dict[str, Any]
    explanation: str
    points: float
    difficulty: str
    curriculum_skill_codes: list[str]
    ct_pillar_codes: list[str]
    source_references: list[dict[str, Any]]
    manual_grading: bool
    shuffle_options: bool
    question_bank_item_id: UUID | None = None
    source_type: str = "teacher"
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    item_version: int = 1
    item_snapshot_checksum: str = ""
    is_annulled: bool = False
    annulment_reason: str | None = None


class StudentQuestionRead(BaseModel):
    id: UUID
    position: int
    question_type: QuestionType
    prompt: str
    options: list[dict[str, Any]]
    points: float
    difficulty: str
    curriculum_skill_codes: list[str]
    ct_pillar_codes: list[str]


class AssignmentSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    package_id: UUID | None
    assessment_version_id: UUID | None = None
    title: str
    instructions: str
    assignment_type: AssignmentType
    status: AssignmentStatus
    available_from: datetime | None
    due_at: datetime | None
    time_limit_minutes: int | None
    maximum_attempts: int
    maximum_score: float
    feedback_policy: FeedbackPolicy
    answer_key_policy: AnswerKeyPolicy
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AssignmentTeacherRead(AssignmentSummaryRead):
    organization_id: UUID
    created_by_user_id: UUID
    created_by_name_snapshot: str
    material_snapshot: dict[str, Any]
    snapshot_version: int
    minimum_score: float | None
    randomize_questions: bool
    randomize_options: bool
    allow_pause: bool
    allow_late_submission: bool
    late_penalty_percent: float
    show_result_immediately: bool
    results_released_at: datetime | None
    settings: dict[str, Any]
    recipients: list[RecipientRead]
    questions: list[TeacherQuestionRead]


class StudentAssignmentCard(BaseModel):
    id: UUID
    title: str
    assignment_type: AssignmentType
    status: str
    available_from: datetime | None
    due_at: datetime | None
    time_limit_minutes: int | None
    maximum_attempts: int
    attempts_used: int
    progress_status: str
    best_percentage: float | None
    is_late: bool
    accommodations: dict[str, Any]


class StudentAssignmentDetail(BaseModel):
    id: UUID
    title: str
    instructions: str
    assignment_type: AssignmentType
    available_from: datetime | None
    due_at: datetime | None
    time_limit_minutes: int | None
    maximum_attempts: int
    attempts_used: int
    maximum_score: float
    material: dict[str, Any]
    progress_status: str
    can_start: bool
    active_attempt_id: UUID | None
    accommodations: dict[str, Any]


class AttemptStartRequest(BaseModel):
    preview_mode: bool = False


class AnswerSaveRequest(BaseModel):
    answer_payload: dict[str, Any] = Field(default_factory=dict)
    response_time_seconds: int = Field(default=0, ge=0, le=86400)
    expected_revision: int | None = Field(default=None, ge=0)


class AttemptSubmitRequest(BaseModel):
    confirm_submission: bool = True
    time_spent_seconds: int = Field(default=0, ge=0, le=7 * 86400)


class StudentAnswerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question_id: UUID
    answer_payload: dict[str, Any]
    is_correct: bool | None
    awarded_score: float
    response_time_seconds: int
    teacher_feedback: str | None
    updated_at: datetime


class AttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assignment_id: UUID
    student_id: UUID
    attempt_number: int
    status: AttemptStatus
    started_at: datetime
    last_saved_at: datetime | None
    submitted_at: datetime | None
    graded_at: datetime | None
    score: float
    percentage: float
    time_spent_seconds: int
    teacher_feedback: str | None
    grading_complete: bool
    is_late: bool
    late_penalty_applied: float
    time_limit_minutes_snapshot: int | None
    maximum_attempts_snapshot: int
    randomization_state: dict[str, Any]
    autosave_revision: int
    answers: list[StudentAnswerRead] = Field(default_factory=list)


class AttemptWorkspace(BaseModel):
    attempt: AttemptRead
    questions: list[StudentQuestionRead]
    material: dict[str, Any]
    feedback_policy: FeedbackPolicy
    answer_key_policy: AnswerKeyPolicy


class AnswerSaveResponse(BaseModel):
    answer: StudentAnswerRead
    autosave_revision: int
    feedback_available: bool
    is_correct: bool | None = None
    feedback: str | None = None


class AttemptResultAnswer(BaseModel):
    question_id: UUID
    prompt: str
    answer_payload: dict[str, Any]
    awarded_score: float
    is_correct: bool | None
    feedback: str | None
    correct_answer: dict[str, Any] | None = None
    explanation: str | None = None


class AttemptResult(BaseModel):
    attempt_id: UUID
    status: AttemptStatus
    score: float
    percentage: float
    maximum_score: float
    grading_complete: bool
    result_available: bool
    answer_key_available: bool
    teacher_feedback: str | None
    answers: list[AttemptResultAnswer]


class ManualGradeRequest(BaseModel):
    awarded_score: float = Field(ge=0, le=10000)
    is_correct: bool | None = None
    teacher_feedback: str | None = Field(default=None, max_length=5000)


class AttemptReopenRequest(BaseModel):
    reason: str = Field(default="Nova oportunidade concedida pelo professor", max_length=2000)


class RecipientUpdate(BaseModel):
    available_from_override: datetime | None = None
    due_at_override: datetime | None = None
    maximum_attempts_override: int | None = Field(default=None, ge=1, le=20)
    time_limit_minutes_override: int | None = Field(default=None, ge=1, le=1440)
    accommodations: dict[str, Any] | None = None
    status: RecipientStatus | None = None


class LearningEventCreate(BaseModel):
    event_type: str = Field(min_length=2, max_length=60)
    attempt_id: UUID | None = None
    question_id: UUID | None = None
    page_number: int | None = Field(default=None, ge=1, le=10000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StudentProgressRow(BaseModel):
    student_id: UUID
    student_name: str
    student_email: str
    progress_status: str
    attempts_count: int
    best_score: float | None
    best_percentage: float | None
    last_activity_at: datetime | None
    is_late: bool


class QuestionProgressRow(BaseModel):
    question_id: UUID
    position: int
    prompt: str
    response_count: int
    automatically_graded_count: int
    correct_count: int
    correct_rate: float | None
    average_score: float | None
    most_common_wrong_answer: dict[str, Any] | None


class AssignmentProgress(BaseModel):
    assignment_id: UUID
    total_students: int
    not_started: int
    in_progress: int
    submitted: int
    graded: int
    average_percentage: float | None
    completion_rate: float
    students: list[StudentProgressRow]
    questions: list[QuestionProgressRow]


class GradingQueueItem(BaseModel):
    answer_id: UUID
    attempt_id: UUID
    student_id: UUID
    student_name: str
    question_id: UUID
    question_prompt: str
    answer_payload: dict[str, Any]
    maximum_points: float
    awarded_score: float
    teacher_feedback: str | None


class StudentPreview(BaseModel):
    assignment: StudentAssignmentDetail
    questions: list[StudentQuestionRead]
    note: str = "Prévia sem registro de tentativa ou resposta."


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assignment_id: UUID | None
    notification_type: str
    title: str
    message: str
    action_path: str | None
    status: NotificationStatus
    created_at: datetime
    read_at: datetime | None


class ClassroomAnnouncementCreate(BaseModel):
    classroom_ids: list[UUID] = Field(min_length=1, max_length=50)
    title: str = Field(min_length=3, max_length=240)
    message: str = Field(min_length=3, max_length=2000)
    action_path: str = Field(default="/aluno", min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_action_path(self) -> "ClassroomAnnouncementCreate":
        if len(self.title.strip()) < 3 or len(self.message.strip()) < 3:
            raise ValueError("título e mensagem devem conter conteúdo")
        if not self.action_path.startswith("/") or self.action_path.startswith("//"):
            raise ValueError("action_path deve ser uma rota interna")
        return self


class ClassroomAnnouncementResult(BaseModel):
    classrooms: int
    recipients: int


class GrantExtraAttemptRequest(BaseModel):
    additional_attempts: int = Field(default=1, ge=1, le=10)
    due_at_override: datetime | None = None
    reason: str = Field(default="Tentativa adicional liberada pelo professor", max_length=2000)


class AssignmentDuplicateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=240)
    copy_recipients: bool = True
