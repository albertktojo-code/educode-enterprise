from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.analytics import (
    AlertSeverity,
    AlertStatus,
    AnalyticsJobStatus,
    InterventionStatus,
    InterventionType,
)

AttemptPolicy = Literal["first", "latest", "best", "all"]


class AnalyticsRefreshRequest(BaseModel):
    attempt_policy: AttemptPolicy = "best"
    classroom_id: UUID | None = None
    assignment_id: UUID | None = None
    student_id: UUID | None = None
    create_snapshots: bool = True
    generate_alerts: bool = True


class AnalyticsRefreshRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: AnalyticsJobStatus
    attempt_policy: str
    filters: dict[str, Any]
    result_summary: dict[str, Any]
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class DashboardSummary(BaseModel):
    students_count: int
    assignments_count: int
    completion_rate: float
    average_percentage: float | None
    students_needing_attention: int
    difficult_questions: int
    open_alerts: int
    pending_manual_grading: int
    latest_refresh_at: datetime | None
    attempt_policy: AttemptPolicy = "best"


class TrendPoint(BaseModel):
    label: str
    value: float
    evidence_count: int = 0


class SkillMetricRead(BaseModel):
    skill_code: str
    ct_pillar_code: str
    proficiency_score: float
    confidence_score: float
    evidence_count: int
    correct_count: int
    total_count: int
    mastery_level: str
    last_activity_at: datetime | None


class StudentActivityMetric(BaseModel):
    assignment_id: UUID
    assignment_title: str
    attempt_number: int
    percentage: float
    score: float
    time_spent_seconds: int
    submitted_at: datetime | None
    status: str


class StudentAnalyticsRead(BaseModel):
    student_id: UUID
    student_name: str
    student_email: str
    average_percentage: float | None
    activities_completed: int
    total_attempts: int
    average_time_seconds: float | None
    trend: list[TrendPoint]
    skills: list[SkillMetricRead]
    activities: list[StudentActivityMetric]
    recommendations: list[str]


class ClassroomStudentRow(BaseModel):
    student_id: UUID
    student_name: str
    average_percentage: float | None
    assignments_completed: int
    trend_direction: str
    attention_level: str


class ClassroomAnalyticsRead(BaseModel):
    classroom_id: UUID
    classroom_name: str
    student_count: int
    assignment_count: int
    average_percentage: float | None
    median_percentage: float | None
    completion_rate: float
    average_time_seconds: float | None
    skills: list[SkillMetricRead]
    students: list[ClassroomStudentRow]
    trend: list[TrendPoint]


class DistractorRow(BaseModel):
    answer: str
    count: int
    percentage: float
    is_correct_option: bool = False


class QuestionAnalyticsRead(BaseModel):
    question_id: UUID
    assignment_id: UUID
    position: int
    prompt: str
    response_count: int
    correct_count: int
    correct_rate: float | None
    difficulty_index: float | None
    difficulty_label: str
    discrimination_index: float | None
    average_response_time: float | None
    omission_rate: float | None
    average_awarded_score: float | None
    distractors: list[DistractorRow]
    curriculum_skill_codes: list[str]
    ct_pillar_codes: list[str]


class AssignmentAnalyticsRead(BaseModel):
    assignment_id: UUID
    assignment_title: str
    participant_count: int
    attempt_count: int
    completion_rate: float
    average_percentage: float | None
    median_percentage: float | None
    average_time_seconds: float | None
    questions: list[QuestionAnalyticsRead]
    trend: list[TrendPoint]
    data_quality_notes: list[str]


class LearningAlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    classroom_id: UUID | None
    student_id: UUID | None
    assignment_id: UUID | None
    alert_type: str
    severity: AlertSeverity
    status: AlertStatus
    title: str
    description: str
    explanation: str
    evidence: dict[str, Any]
    rule_code: str
    created_at: datetime
    resolved_at: datetime | None


class AlertUpdateRequest(BaseModel):
    status: AlertStatus


class InterventionCreate(BaseModel):
    classroom_id: UUID | None = None
    student_id: UUID | None = None
    alert_id: UUID | None = None
    assignment_id: UUID | None = None
    intervention_type: InterventionType
    reason: str = Field(min_length=3, max_length=5000)
    notes: str = Field(default="", max_length=10000)
    expected_outcome: str = Field(default="", max_length=5000)

    @model_validator(mode="after")
    def target_required(self) -> "InterventionCreate":
        if self.classroom_id is None and self.student_id is None:
            raise ValueError("Informe uma turma ou estudante")
        return self


class InterventionUpdate(BaseModel):
    status: InterventionStatus | None = None
    notes: str | None = Field(default=None, max_length=10000)
    expected_outcome: str | None = Field(default=None, max_length=5000)
    result_summary: str | None = Field(default=None, max_length=10000)


class InterventionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    teacher_id: UUID
    classroom_id: UUID | None
    student_id: UUID | None
    alert_id: UUID | None
    assignment_id: UUID | None
    intervention_type: InterventionType
    status: InterventionStatus
    reason: str
    notes: str
    expected_outcome: str
    result_summary: str
    created_at: datetime
    completed_at: datetime | None


class DataQualityRead(BaseModel):
    status: str
    valid_attempts: int
    incomplete_attempts: int
    manually_graded_answers: int
    unanswered_items: int
    assignments_with_no_questions: int
    notes: list[str]


class StudentOwnProgressRead(BaseModel):
    student_id: UUID
    average_percentage: float | None
    completed_activities: int
    trend: list[TrendPoint]
    strengths: list[SkillMetricRead]
    development_areas: list[SkillMetricRead]
    next_steps: list[str]


class AnimeProgressMilestoneRead(BaseModel):
    percentage: int
    student_count: int
    reach_rate: float


class AnimeCheckpointAnalyticsRead(BaseModel):
    checkpoint_id: UUID
    label: str
    timestamp_ms: int
    assignment_id: UUID
    reached_students: int
    completed_students: int
    completion_rate: float
    average_percentage: float | None


class AnimeAnalyticsRead(BaseModel):
    project_id: UUID
    title: str
    render_revision: int | None
    play_count: int
    viewer_count: int
    completed_viewer_count: int
    video_completion_rate: float
    average_max_progress: float
    milestones: list[AnimeProgressMilestoneRead]
    checkpoints: list[AnimeCheckpointAnalyticsRead]
    data_quality_notes: list[str]
