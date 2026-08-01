export interface AssessmentPublication {
  id: string;
  code: string;
  title: string;
  version: number;
  status: string;
  starts_at: string;
  ends_at: string;
  duration_minutes: number;
  max_attempts: number;
  navigation_mode: string;
  item_snapshot: Array<{ question_version_id: string; position: number }>;
}

export interface MonitoringSummary {
  publication_id: string;
  total_sessions: number;
  status_counts: Record<string, number>;
  active_sessions: number;
  submitted_sessions: number;
  attention_sessions: number;
  average_progress: number;
  last_updated_at: string;
}

export interface AvailableAssessment {
  publication: AssessmentPublication;
  effective_status: string;
  attempts_used: number;
  attempts_allowed: number;
  can_start: boolean;
  reason?: string | null;
}
