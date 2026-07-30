export type HintLevel =
  | "ORIENTATION"
  | "STRATEGY"
  | "SPECIFIC"
  | "SIMILAR_EXAMPLE"
  | "GUIDED_SOLUTION";

export type ProgressionAction =
  | "ADVANCE"
  | "MAINTAIN"
  | "REVIEW"
  | "REINFORCE"
  | "RETURN_TO_PREREQUISITE"
  | "TEACHER_REVIEW"
  | "COMPLETE_PATH"
  | "SUSPEND_ADAPTATION";

export type AdaptationType =
  | "PLAIN_LANGUAGE"
  | "LARGE_PRINT"
  | "HIGH_CONTRAST"
  | "EASY_READING"
  | "IMAGE_DESCRIPTION"
  | "AUDIO_DESCRIPTION"
  | "SCREEN_READER"
  | "CAPTIONS"
  | "REDUCED_VISUAL_STIMULUS"
  | "STEP_BY_STEP"
  | "VISUAL_SUPPORT"
  | "OBJECTIVE_INSTRUCTIONS"
  | "KEYBOARD_NAVIGATION";

export interface SpacedReviewResult {
  interval_days: number;
  scheduled_for: string;
  status: string;
  priority: number;
  reason: string;
  rule_version: string;
}

export interface FeedbackResult {
  feedback_type: string;
  content: string;
  next_action: ProgressionAction;
  explanation: string;
  requires_teacher_review: boolean;
  rule_version: string;
}

export interface IndividualDifficultyResult {
  difficulty_score: number;
  difficulty_level: string;
  confidence_score: number;
  change: number;
  action: string;
  reason: string;
  requires_teacher_review: boolean;
  calculation_version: string;
}

export interface ObservedDifficultyResult {
  predicted_difficulty: number;
  observed_difficulty: number | null;
  difference: number | null;
  classification: string;
  sample_size: number;
  confidence_score: number;
  metrics: Record<string, number>;
  requires_review: boolean;
  calculation_version: string;
}

export interface AccessibleVersionPreview {
  title: string;
  content: string;
  adaptation_type: AdaptationType;
  accessibility_metadata: Record<string, unknown>;
  pedagogical_snapshot: Record<string, unknown>;
  equivalence_status: string;
  generation_method: string;
  status: string;
  warnings: string[];
}


export interface GraduatedHint {
  id: string;
  organization_id: string;
  resource_type: string;
  resource_id: string;
  question_id: string | null;
  learning_node_id: string | null;
  level: HintLevel;
  level_order: number;
  title: string;
  content: string;
  release_rule: Record<string, unknown>;
  penalty_rule: Record<string, unknown>;
  version: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ProgressionRule {
  id: string;
  organization_id: string;
  name: string;
  version: string;
  description: string;
  scope_type: string;
  scope_id: string | null;
  conditions: Record<string, unknown>;
  result_action: ProgressionAction;
  priority: number;
  requires_teacher_approval: boolean;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AccessibleVersionRecord {
  id: string;
  organization_id: string;
  source_resource_type: string;
  source_resource_id: string;
  adaptation_type: AdaptationType;
  title: string;
  content: string;
  accessibility_metadata: Record<string, unknown>;
  pedagogical_snapshot: Record<string, unknown>;
  pedagogical_equivalence_status: string;
  generation_method: string;
  version: number;
  status: string;
  created_at: string;
  updated_at: string;
}
