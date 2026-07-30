from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudyStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class DatasetStatus(StrEnum):
    BUILDING = "building"
    FROZEN = "frozen"
    INVALID = "invalid"


class AnalysisStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    IN_REVIEW = "in_review"
    APPROVED = "approved"


class ReportType(StrEnum):
    TEACHER = "teacher"
    STATISTICAL = "statistical"
    ACADEMIC = "academic"


class StatisticalStudy(Base):
    __tablename__ = "statistical_studies"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    research_question: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    null_hypothesis: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    alternative_hypothesis: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    study_design: Mapped[str] = mapped_column(String(80), default="pre_post", nullable=False)
    significance_level: Mapped[float] = mapped_column(Float, default=0.05, nullable=False)
    pedagogical_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[StudyStatus] = mapped_column(Enum(StudyStatus, name="statistical_study_status"), default=StudyStatus.DRAFT, nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class StatisticalDataset(Base):
    __tablename__ = "statistical_datasets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    study_id: Mapped[UUID] = mapped_column(ForeignKey("statistical_studies.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[DatasetStatus] = mapped_column(Enum(DatasetStatus, name="statistical_dataset_status"), default=DatasetStatus.BUILDING, nullable=False)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    attempt_policy: Mapped[str] = mapped_column(String(30), default="first", nullable=False)
    participant_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dataset_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    quality_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    variable_dictionary: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    rows_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    anonymized: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StatisticalAnalysis(Base):
    __tablename__ = "statistical_analyses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    study_id: Mapped[UUID] = mapped_column(ForeignKey("statistical_studies.id", ondelete="CASCADE"), index=True)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("statistical_datasets.id", ondelete="RESTRICT"), index=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    analysis_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    assumptions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    descriptive_results: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    test_results: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    effect_size: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    confidence_intervals: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    interpretation_teacher: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    interpretation_researcher: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    limitations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    software_versions: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[AnalysisStatus] = mapped_column(Enum(AnalysisStatus, name="statistical_analysis_status"), default=AnalysisStatus.PENDING, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    parent_analysis_id: Mapped[UUID | None] = mapped_column(ForeignKey("statistical_analyses.id", ondelete="SET NULL"), index=True, nullable=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    configuration_checksum: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    result_signature: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    review_status: Mapped[str] = mapped_column(String(40), default="draft", nullable=False)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StatisticalChart(Base):
    __tablename__ = "statistical_charts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    analysis_id: Mapped[UUID] = mapped_column(ForeignKey("statistical_analyses.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    chart_type: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    data_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    alt_text: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    include_in_report: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StatisticalReport(Base):
    __tablename__ = "statistical_reports"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    study_id: Mapped[UUID] = mapped_column(ForeignKey("statistical_studies.id", ondelete="CASCADE"), index=True)
    analysis_id: Mapped[UUID] = mapped_column(ForeignKey("statistical_analyses.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    report_type: Mapped[ReportType] = mapped_column(Enum(ReportType, name="statistical_report_type"), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    content_html: Mapped[str] = mapped_column(Text(), nullable=False)
    sections: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    review_status: Mapped[str] = mapped_column(String(40), default="draft", nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StatisticalSensitivityRun(Base):
    __tablename__ = "statistical_sensitivity_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    base_analysis_id: Mapped[UUID] = mapped_column(ForeignKey("statistical_analyses.id", ondelete="CASCADE"), index=True)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("statistical_datasets.id", ondelete="RESTRICT"), index=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    scenario_key: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    scenario_parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    analysis_type: Mapped[str] = mapped_column(String(80), nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    conclusion_changed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StatisticalMethodComparison(Base):
    __tablename__ = "statistical_method_comparisons"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    base_analysis_id: Mapped[UUID] = mapped_column(ForeignKey("statistical_analyses.id", ondelete="CASCADE"), index=True)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("statistical_datasets.id", ondelete="RESTRICT"), index=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    methods: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    results: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    conclusions_consistent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StatisticalReviewComment(Base):
    __tablename__ = "statistical_review_comments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    entity_type: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    entity_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    section_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    body: Mapped[str] = mapped_column(Text(), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    resolved_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StatisticalReportRevision(Base):
    __tablename__ = "statistical_report_revisions"
    __table_args__ = (
        UniqueConstraint(
            "report_id", "version_number", name="uq_statistical_report_revision_version"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    report_id: Mapped[UUID] = mapped_column(ForeignKey("statistical_reports.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_html: Mapped[str] = mapped_column(Text(), nullable=False)
    sections: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    change_summary: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StatisticalSampleSizePlan(Base):
    __tablename__ = "statistical_sample_size_plans"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    study_id: Mapped[UUID | None] = mapped_column(ForeignKey("statistical_studies.id", ondelete="SET NULL"), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    design: Mapped[str] = mapped_column(String(60), nullable=False)
    significance_level: Mapped[float] = mapped_column(Float, default=0.05, nullable=False)
    power: Mapped[float] = mapped_column(Float, default=0.80, nullable=False)
    expected_effect_size: Mapped[float] = mapped_column(Float, nullable=False)
    group_ratio: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
