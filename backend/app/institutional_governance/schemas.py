from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .policies import ASSET_TYPES, DECISIONS, REVIEW_STAGES, RISK_TIERS


class GovernanceAssetCreate(BaseModel):
    code: str = Field(min_length=3, max_length=120)
    name: str = Field(min_length=3, max_length=240)
    asset_type: str
    risk_tier: str = "moderate"
    adaptive_model_version_id: uuid.UUID | None = None
    ai_model_id: uuid.UUID | None = None
    prompt_template_id: uuid.UUID | None = None
    module_policy_id: uuid.UUID | None = None
    intervention_type: str | None = Field(default=None, max_length=80)
    evidence_rule_code: str | None = Field(default=None, max_length=120)
    purpose: str = Field(default="", max_length=10000)
    intended_users: list[str] = Field(default_factory=list, max_length=30)
    limitations: list[str] = Field(default_factory=list, max_length=50)
    prohibited_uses: list[str] = Field(default_factory=list, max_length=50)
    documentation: dict[str, Any] = Field(default_factory=dict)
    approval_policy: dict[str, Any] = Field(default_factory=dict)
    monitoring_policy: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_asset(self):
        self.asset_type = self.asset_type.lower()
        self.risk_tier = self.risk_tier.lower()
        if self.asset_type not in ASSET_TYPES:
            raise ValueError("Tipo de ativo de governança inválido")
        if self.risk_tier not in RISK_TIERS:
            raise ValueError("Nível de risco inválido")
        references = [
            self.adaptive_model_version_id,
            self.ai_model_id,
            self.prompt_template_id,
            self.module_policy_id,
            self.intervention_type,
            self.evidence_rule_code,
        ]
        if sum(value is not None and value != "" for value in references) != 1:
            raise ValueError("Informe exatamente uma referência governada")
        expected = {
            "adaptive_model": self.adaptive_model_version_id,
            "ai_model": self.ai_model_id,
            "prompt_template": self.prompt_template_id,
            "module_policy": self.module_policy_id,
            "intervention_strategy": self.intervention_type,
            "evidence_rule": self.evidence_rule_code,
        }[self.asset_type]
        if not expected:
            raise ValueError("A referência não corresponde ao tipo do ativo")
        return self


class GovernanceAssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=240)
    risk_tier: str | None = None
    purpose: str | None = Field(default=None, max_length=10000)
    intended_users: list[str] | None = Field(default=None, max_length=30)
    limitations: list[str] | None = Field(default=None, max_length=50)
    prohibited_uses: list[str] | None = Field(default=None, max_length=50)
    documentation: dict[str, Any] | None = None
    approval_policy: dict[str, Any] | None = None
    monitoring_policy: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_risk(self):
        if self.risk_tier:
            self.risk_tier = self.risk_tier.lower()
            if self.risk_tier not in RISK_TIERS:
                raise ValueError("Nível de risco inválido")
        return self


class GovernanceReviewCreate(BaseModel):
    review_stage: str
    decision: str
    scorecard: dict[str, Any] = Field(default_factory=dict)
    findings: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    required_actions: list[str] = Field(default_factory=list, max_length=100)
    comments: str = Field(default="", max_length=10000)

    @model_validator(mode="after")
    def validate_review(self):
        self.review_stage = self.review_stage.lower()
        self.decision = self.decision.lower()
        if self.review_stage not in REVIEW_STAGES:
            raise ValueError("Etapa de revisão inválida")
        if self.decision not in DECISIONS:
            raise ValueError("Decisão de revisão inválida")
        if self.decision != "approved" and not self.comments.strip():
            raise ValueError("Rejeição ou solicitação de ajuste exige justificativa")
        return self


class GovernanceActionRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=10000)


class GovernanceIncidentCreate(BaseModel):
    category: str = Field(min_length=3, max_length=50)
    severity: str = Field(default="moderate")
    title: str = Field(min_length=3, max_length=240)
    description: str = Field(min_length=5, max_length=20000)
    evidence: dict[str, Any] = Field(default_factory=dict)
    remediation_plan: list[dict[str, Any]] = Field(
        default_factory=list,
        max_length=100,
    )

    @model_validator(mode="after")
    def validate_severity(self):
        self.severity = self.severity.lower()
        if self.severity not in {"low", "moderate", "high", "critical"}:
            raise ValueError("Severidade inválida")
        return self


class GovernanceIncidentResolve(BaseModel):
    resolution_summary: str = Field(min_length=5, max_length=20000)


class GovernanceRefreshRequest(BaseModel):
    period_start: date | None = None
    period_end: date | None = None
    asset_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)
    open_incidents: bool = True

    @model_validator(mode="after")
    def validate_period(self):
        if (
            self.period_start
            and self.period_end
            and self.period_end < self.period_start
        ):
            raise ValueError("Período inválido")
        return self


class GovernanceBootstrapRequest(BaseModel):
    include_adaptive_models: bool = True
    include_ai_models: bool = True
    include_prompt_templates: bool = True
    include_module_policies: bool = True
    include_intervention_types: bool = True
    include_evidence_rules: bool = True


class GovernanceVersionCreate(BaseModel):
    change_summary: str = Field(min_length=5, max_length=10000)
