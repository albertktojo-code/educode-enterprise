export type MasteryLevel =
  | 'not_assessed'
  | 'insufficient_evidence'
  | 'initial'
  | 'developing'
  | 'adequate'
  | 'advanced'

export type SkillState = {
  id: string
  student_id: string
  dimension_type: string
  dimension_code: string
  mastery_score: number
  mastery_level: MasteryLevel
  confidence_score: number
  confidence_level: string
  evidence_count: number
  trend: string
  calculation_explanation: string
  first_evidence_at: string | null
  last_evidence_at: string | null
  calculated_at: string
}

export type AdaptiveProfile = {
  id: string
  student_id: string
  status: string
  preferred_formats: string[]
  accessibility_preferences: Record<string, unknown>
  teacher_notes: string
  last_calculated_at: string | null
  created_at: string
}

export type Recommendation = {
  id: string
  student_id: string | null
  classroom_id: string | null
  group_id: string | null
  recommendation_type: string
  status: string
  priority: string
  title: string
  rationale: string
  target_dimension_type: string
  target_dimension_code: string
  target_mastery: number
  confidence_score: number
  evidence_summary: Record<string, unknown>
  proposed_materials: Array<Record<string, unknown>>
  created_by_ai: boolean
  review_notes: string
  reviewed_at: string | null
  created_at: string
}

export type PathStep = {
  id: string
  path_id: string
  assignment_id: string | null
  position: number
  step_type: string
  title: string
  description: string
  content_reference: Record<string, unknown>
  is_required: boolean
  status: string
  advancement_rule: Record<string, unknown>
  due_at: string | null
  available_at: string | null
  completed_at: string | null
  completion_snapshot: Record<string, unknown>
}

export type LearningPath = {
  id: string
  student_id: string | null
  classroom_id: string | null
  group_id: string | null
  recommendation_id: string | null
  title: string
  description: string
  path_type: string
  status: string
  goal: string
  target_dimension_type: string
  target_dimension_code: string
  target_mastery: number
  minimum_evidence_count: number
  settings_json: Record<string, unknown>
  approved_at: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  steps: PathStep[]
}

export type ReviewSchedule = {
  id: string
  student_id: string
  path_id: string | null
  step_id: string | null
  dimension_type: string
  dimension_code: string
  review_number: number
  scheduled_for: string
  status: string
  completed_at: string | null
  outcome_snapshot: Record<string, unknown>
}

export type AdaptiveDashboard = {
  students_with_profiles: number
  active_paths: number
  pending_recommendations: number
  scheduled_reviews: number
  low_confidence_states: number
  dimensions_needing_attention: number
  temporary_groups: number
  recent_recommendations: Recommendation[]
  paths_by_status: Record<string, number>
  mastery_distribution: Record<string, number>
}

export type StudentAdaptiveSummary = {
  profile: AdaptiveProfile
  skill_states: SkillState[]
  active_paths: number
  pending_recommendations: number
  upcoming_reviews: number
  weakest_dimensions: SkillState[]
  strongest_dimensions: SkillState[]
}

export type StudentOwnPath = {
  profile: AdaptiveProfile
  skill_states: SkillState[]
  paths: LearningPath[]
  reviews: ReviewSchedule[]
  explanation: string
}

export type AdaptiveGroup = {
  id: string
  classroom_id: string | null
  name: string
  purpose: string
  target_dimension_type: string
  target_dimension_code: string
  status: string
  is_visible_to_students: boolean
  expires_at: string | null
  created_at: string
  member_count: number
}
