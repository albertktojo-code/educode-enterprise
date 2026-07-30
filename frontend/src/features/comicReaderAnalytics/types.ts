export interface ReaderAnalyticsEventInput {
  release_id: string;
  presentation_session_id?: string;
  session_key: string;
  event_type: string;
  page_number?: number;
  panel_number?: number;
  duration_ms?: number;
  sequence?: number;
  properties?: Record<string, unknown>;
}

export interface ReaderAnalyticsOverview {
  period_start: string;
  period_end: string;
  students: number;
  releases: number;
  sessions: number;
  active_seconds: number;
  completion_rate: number;
  average_progress_percent: number;
  revisits: number;
  glossary_opens: number;
  narration_seconds: number;
  accessibility_actions: number;
  presentation_syncs: number;
}

export interface ContentMetric {
  metric_date: string;
  page_number?: number | null;
  panel_number?: number | null;
  viewer_count: number;
  view_count: number;
  completion_count: number;
  revisit_count: number;
  total_active_seconds: number;
  glossary_opens: number;
  narration_starts: number;
  assessment_opens: number;
}

export interface LearningMetric {
  scope_type: string;
  scope_id?: string | null;
  assignment_id: string;
  sample_size: number;
  average_active_seconds: number;
  average_progress_percent: number;
  average_score_percent: number;
  reading_score_correlation?: number | null;
  completion_score_delta?: number | null;
  interpretation: string;
  privacy_suppressed: boolean;
  evidence: Record<string, unknown>;
}

export interface AccessibilityMetric {
  users: number;
  narration_users: number;
  accessibility_users: number;
  narration_adoption_rate: number;
  accessibility_adoption_rate: number;
  narration_seconds: number;
  accessibility_actions: number;
}
