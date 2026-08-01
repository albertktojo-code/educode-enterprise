export interface GovernanceDashboard {
  asset_counts: Record<string, number>;
  open_incidents: number;
  threshold_breaches: number;
  enforcement_mode: string;
  human_suspension_required: boolean;
}

export interface GovernanceReviewSummary {
  required_stages: string[];
  approved_stages: string[];
  missing_stages: string[];
  approval_count: number;
  required_approvals: number;
  blocked: boolean;
  ready: boolean;
}

export interface GovernanceAsset {
  id: string;
  code: string;
  name: string;
  version: number;
  asset_type: string;
  status: string;
  risk_tier: string;
  owner_user_id: string;
  adaptive_model_version_id?: string | null;
  ai_model_id?: string | null;
  prompt_template_id?: string | null;
  module_policy_id?: string | null;
  intervention_type?: string | null;
  evidence_rule_code?: string | null;
  purpose: string;
  intended_users: string[];
  limitations: string[];
  prohibited_uses: string[];
  documentation: Record<string, unknown>;
  documentation_completeness: number;
  approval_policy: Record<string, unknown>;
  monitoring_policy: Record<string, unknown>;
  lineage_snapshot: Record<string, unknown>;
  content_hash: string;
  review_summary?: GovernanceReviewSummary | null;
  submitted_at?: string | null;
  approved_at?: string | null;
  activated_at?: string | null;
  suspended_at?: string | null;
  retired_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface GovernanceSnapshot {
  id: string;
  asset_id?: string;
  period_start: string;
  period_end: string;
  sample_size: number;
  quality_score?: number | null;
  safety_score?: number | null;
  effectiveness_score?: number | null;
  fairness_score?: number | null;
  drift_score?: number | null;
  error_rate?: number | null;
  recurrence_rate?: number | null;
  threshold_breached: boolean;
  threshold_breaches: Array<Record<string, unknown>>;
  privacy_suppressed: boolean;
  calculated_at: string;
}

export interface GovernanceIncident {
  id: string;
  asset_id: string;
  snapshot_id?: string | null;
  category: string;
  severity: string;
  status: string;
  title: string;
  description: string;
  evidence: Record<string, unknown>;
  remediation_plan: Array<Record<string, unknown>>;
  resolution_summary: string;
  detected_at: string;
  resolved_at?: string | null;
}

export interface GovernanceRefreshResult {
  job_id: string;
  reused: boolean;
  period_start: string;
  period_end: string;
  assets_monitored: number;
  threshold_breaches: number;
  privacy_suppressed: number;
}

export interface GovernanceComparison {
  code: string;
  left: {
    id: string;
    version: number;
    status: string;
    content_hash: string;
    documentation_completeness: number;
    latest_snapshot?: GovernanceSnapshot | null;
  };
  right: {
    id: string;
    version: number;
    status: string;
    content_hash: string;
    documentation_completeness: number;
    latest_snapshot?: GovernanceSnapshot | null;
  };
  documentation_diff: {
    changed_keys: string[];
    unchanged_keys: string[];
    left_hash: string;
    right_hash: string;
  };
  monitoring_policy_diff: {
    changed_keys: string[];
  };
  approval_policy_diff: {
    changed_keys: string[];
  };
}
