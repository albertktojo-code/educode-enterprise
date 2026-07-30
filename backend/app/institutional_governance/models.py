from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .compat import Base


class InstitutionalGovernanceAsset(Base):
    __tablename__ = "institutional_governance_assets"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "code",
            "version",
            name="uq_governance_asset_org_code_version",
        ),
        CheckConstraint(
            """
            num_nonnulls(
                adaptive_model_version_id,
                ai_model_id,
                prompt_template_id,
                module_policy_id,
                intervention_type,
                evidence_rule_code
            ) = 1
            """,
            name="ck_governance_asset_reference",
        ),
        Index(
            "ix_governance_asset_status",
            "organization_id",
            "status",
            "risk_tier",
        ),
        Index(
            "ix_governance_asset_reference",
            "organization_id",
            "asset_type",
            "code",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    asset_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="draft",
        index=True,
    )
    risk_tier: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="moderate",
        index=True,
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    adaptive_model_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("adaptive_model_versions.id", ondelete="SET NULL"),
        index=True,
    )
    ai_model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_models.id", ondelete="SET NULL"),
        index=True,
    )
    prompt_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_prompt_templates.id", ondelete="SET NULL"),
        index=True,
    )
    module_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_module_policies.id", ondelete="SET NULL"),
        index=True,
    )
    intervention_type: Mapped[str | None] = mapped_column(
        String(80),
        index=True,
    )
    evidence_rule_code: Mapped[str | None] = mapped_column(
        String(120),
        index=True,
    )
    purpose: Mapped[str] = mapped_column(Text, nullable=False, default="")
    intended_users: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    limitations: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    prohibited_uses: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    documentation: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    approval_policy: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    monitoring_policy: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    lineage_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="",
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    suspended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class InstitutionalGovernanceReview(Base):
    __tablename__ = "institutional_governance_reviews"
    __table_args__ = (
        UniqueConstraint(
            "asset_id",
            "reviewer_user_id",
            "review_stage",
            name="uq_governance_review_asset_user_stage",
        ),
        Index(
            "ix_governance_review_queue",
            "organization_id",
            "decision",
            "review_stage",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutional_governance_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    review_stage: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )
    decision: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
        index=True,
    )
    scorecard: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    findings: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    required_actions: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    comments: Mapped[str] = mapped_column(Text, nullable=False, default="")
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class InstitutionalGovernanceSnapshot(Base):
    __tablename__ = "institutional_governance_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "asset_id",
            "period_start",
            "period_end",
            name="uq_governance_snapshot_asset_period",
        ),
        Index(
            "ix_governance_snapshot_period",
            "organization_id",
            "period_start",
            "period_end",
        ),
        Index(
            "ix_governance_snapshot_risk",
            "organization_id",
            "threshold_breached",
            "calculated_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutional_governance_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    background_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("background_jobs.id", ondelete="SET NULL"),
        index=True,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    sample_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    quality_score: Mapped[float | None] = mapped_column(Float)
    safety_score: Mapped[float | None] = mapped_column(Float)
    effectiveness_score: Mapped[float | None] = mapped_column(Float)
    fairness_score: Mapped[float | None] = mapped_column(Float)
    drift_score: Mapped[float | None] = mapped_column(Float)
    error_rate: Mapped[float | None] = mapped_column(Float)
    recurrence_rate: Mapped[float | None] = mapped_column(Float)
    complaint_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    threshold_breached: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    threshold_breaches: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    cohort_metrics: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    privacy_suppressed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class InstitutionalGovernanceIncident(Base):
    __tablename__ = "institutional_governance_incidents"
    __table_args__ = (
        Index(
            "ix_governance_incident_open",
            "organization_id",
            "status",
            "severity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutional_governance_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutional_governance_snapshots.id", ondelete="SET NULL"),
        index=True,
    )
    opened_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="moderate",
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="open",
        index=True,
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    remediation_plan: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    resolution_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )


class InstitutionalGovernanceEvent(Base):
    __tablename__ = "institutional_governance_events"
    __table_args__ = (
        Index(
            "ix_governance_event_timeline",
            "organization_id",
            "asset_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutional_governance_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="",
    )
    to_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="",
    )
    event_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
