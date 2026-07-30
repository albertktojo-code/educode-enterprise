export interface InterventionDashboard {
  open_alerts: number;
  pending_proposals: number;
  planned_interventions: number;
  active_interventions: number;
  overdue_interventions: number;
  human_approval_required: boolean;
}

export interface InterventionAlert {
  id: string;
  student_id?: string | null;
  classroom_id?: string | null;
  assignment_id?: string | null;
  alert_type: string;
  severity: string;
  status: string;
  title: string;
  description: string;
  explanation: string;
  evidence: Record<string, unknown>;
  rule_code: string;
  created_at: string;
  has_proposal: boolean;
}

export interface InterventionProposal {
  id: string;
  student_id?: string | null;
  classroom_id?: string | null;
  source_alert_id?: string | null;
  source_comic_release_id?: string | null;
  source_ai_request_id?: string | null;
  ai_requested: boolean;
  recommendation_type: string;
  status: string;
  priority: string;
  title: string;
  rationale: string;
  target_dimension_type: string;
  target_dimension_code: string;
  target_mastery: number;
  confidence_score: number;
  evidence_summary: Record<string, unknown>;
  proposed_materials: Array<Record<string, unknown>>;
  created_by_ai: boolean;
  review_notes: string;
  reviewed_at?: string | null;
  created_at: string;
}

export interface LearningIntervention {
  id: string;
  teacher_id: string;
  student_id?: string | null;
  classroom_id?: string | null;
  alert_id?: string | null;
  assignment_id?: string | null;
  source_recommendation_id?: string | null;
  comic_release_id?: string | null;
  adaptive_path_id?: string | null;
  accessible_resource_version_id?: string | null;
  ai_request_id?: string | null;
  intervention_type: string;
  status: "planned" | "active" | "completed" | "canceled";
  reason: string;
  notes: string;
  expected_outcome: string;
  result_summary: string;
  plan_snapshot: {
    actions?: Array<Record<string, unknown>>;
  };
  baseline_snapshot: Record<string, unknown>;
  target_snapshot: Record<string, unknown>;
  human_review_required: boolean;
  approved_at?: string | null;
  started_at?: string | null;
  due_at?: string | null;
  evaluation_due_at?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface StudentIntervention {
  id: string;
  intervention_type: string;
  status: "planned" | "active" | "completed";
  expected_outcome: string;
  student_message: string;
  result_summary: string;
  actions: Array<Record<string, unknown>>;
  comic_release_id?: string | null;
  assignment_id?: string | null;
  adaptive_path_id?: string | null;
  due_at?: string | null;
  created_at: string;
  completed_at?: string | null;
  scope: "student" | "classroom";
}

export interface InterventionOutcome {
  id?: string | null;
  mastery_before?: number | null;
  mastery_after?: number | null;
  mastery_gain?: number | null;
  metric?: string | null;
  before?: number | null;
  after?: number | null;
  gain?: number | null;
  outcome?: string | null;
  improved?: boolean | null;
  target_met?: boolean | null;
  comparable?: boolean | null;
  occurred_at?: string | null;
}

export interface InterventionTimelineEvent {
  id: string;
  event_type: string;
  actor_user_id?: string | null;
  from_status: string;
  to_status: string;
  event_data: Record<string, unknown>;
  created_at: string;
}
