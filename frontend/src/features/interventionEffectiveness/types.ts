export interface EffectivenessWindow {
  code: string;
  days: number;
}

export interface EffectivenessMetric {
  id: string;
  scope_type: string;
  scope_key: string;
  period_start: string;
  period_end: string;
  window_code: string;
  dimension_type: string;
  dimension_key: string;
  intervention_type?: string | null;
  comic_release_id?: string | null;
  assignment_id?: string | null;
  accessible_resource_version_id?: string | null;
  adaptive_path_used?: boolean | null;
  sample_size: number;
  completion_rate?: number | null;
  improved_rate?: number | null;
  target_met_rate?: number | null;
  retention_rate?: number | null;
  recurrence_rate?: number | null;
  average_gain?: number | null;
  median_days_to_improvement?: number | null;
  privacy_suppressed: boolean;
  calculated_at: string;
}

export interface EffectivenessDashboard {
  period_start: string;
  period_end: string;
  completed_interventions: number;
  pending_checkpoints: number;
  overdue_checkpoints: number;
  windows: EffectivenessMetric[];
  privacy_applied: boolean;
}

export interface EvaluationCheckpoint {
  id: string;
  intervention_id: string;
  student_id?: string | null;
  classroom_id?: string | null;
  comic_release_id?: string | null;
  assignment_id?: string | null;
  window_code: string;
  window_days: number;
  scheduled_for: string;
  status: string;
  metric_name: string;
  baseline_value?: number | null;
  observed_value?: number | null;
  delta_value?: number | null;
  target_value?: number | null;
  target_met: boolean;
  improved: boolean;
  retained: boolean;
  alert_recurred: boolean;
  comparable: boolean;
  evidence_count: number;
  privacy_suppressed: boolean;
  evaluated_at?: string | null;
}

export interface EffectivenessRefreshResult {
  job_id: string;
  reused: boolean;
  interventions_scheduled: number;
  checkpoints_evaluated: Record<string, number>;
  metrics_calculated: number;
}
