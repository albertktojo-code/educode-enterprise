export type RecommendationAction =
  | "REPEAT_INTERVENTION"
  | "TRY_ALTERNATIVE"
  | "ADVANCE"
  | "REVIEW_PREREQUISITE"
  | "TEACHER_REVIEW"
  | "COLLECT_MORE_EVIDENCE";

export interface MaterialEffectivenessResult {
  sample_size: number;
  completion_rate: number;
  accuracy_rate: number | null;
  average_gain: number | null;
  median_gain: number | null;
  average_attempts: number;
  average_hints: number;
  average_duration_seconds: number;
  confidence: number;
  classification: string;
  warnings: string[];
}

export interface SimulationDecision {
  student_id: string;
  learning_node_id: string;
  action: RecommendationAction;
  reason: string;
  score: number;
}

export interface SimulationResult {
  profiles_count: number;
  decisions: SimulationDecision[];
  action_distribution: Record<string, number>;
  warnings: string[];
  is_simulation: boolean;
}

export interface AdaptiveModelRecord {
  id: string;
  name: string;
  version: string;
  description: string;
  scope_type: string;
  algorithm_type: string;
  configuration: Record<string, unknown>;
  configuration_hash: string;
  status: string;
  created_at: string;
}

export interface ControlledExperimentRecord {
  id: string;
  name: string;
  description: string;
  hypothesis: string;
  primary_metric: string;
  metric_direction: string;
  strategies: Array<{ key: string; name: string }>;
  minimum_sample_per_strategy: number;
  status: string;
  created_at: string;
}
