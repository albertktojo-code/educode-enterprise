export type AttemptPolicy = 'first' | 'latest' | 'best' | 'all'

export interface DashboardSummary {
  students_count: number
  assignments_count: number
  completion_rate: number
  average_percentage: number | null
  students_needing_attention: number
  difficult_questions: number
  open_alerts: number
  pending_manual_grading: number
  latest_refresh_at: string | null
  attempt_policy: AttemptPolicy
}

export interface TrendPoint { label: string; value: number; evidence_count: number }

export interface SkillMetric {
  skill_code: string
  ct_pillar_code: string
  proficiency_score: number
  confidence_score: number
  evidence_count: number
  correct_count: number
  total_count: number
  mastery_level: string
  last_activity_at: string | null
}

export interface DataQuality {
  status: string
  valid_attempts: number
  incomplete_attempts: number
  manually_graded_answers: number
  unanswered_items: number
  assignments_with_no_questions: number
  notes: string[]
}

export interface LearningAlert {
  id: string
  classroom_id: string | null
  student_id: string | null
  assignment_id: string | null
  alert_type: string
  severity: 'info' | 'attention' | 'priority'
  status: 'open' | 'acknowledged' | 'resolved' | 'dismissed'
  title: string
  description: string
  explanation: string
  evidence: Record<string, unknown>
  rule_code: string
  created_at: string
  resolved_at: string | null
}

export interface ClassroomStudentRow {
  student_id: string
  student_name: string
  average_percentage: number | null
  assignments_completed: number
  trend_direction: 'up' | 'down' | 'stable'
  attention_level: 'normal' | 'attention' | 'priority'
}

export interface ClassroomAnalytics {
  classroom_id: string
  classroom_name: string
  student_count: number
  assignment_count: number
  average_percentage: number | null
  median_percentage: number | null
  completion_rate: number
  average_time_seconds: number | null
  skills: SkillMetric[]
  students: ClassroomStudentRow[]
  trend: TrendPoint[]
}

export interface StudentActivityMetric {
  assignment_id: string
  assignment_title: string
  attempt_number: number
  percentage: number
  score: number
  time_spent_seconds: number
  submitted_at: string | null
  status: string
}

export interface StudentAnalytics {
  student_id: string
  student_name: string
  student_email: string
  average_percentage: number | null
  activities_completed: number
  total_attempts: number
  average_time_seconds: number | null
  trend: TrendPoint[]
  skills: SkillMetric[]
  activities: StudentActivityMetric[]
  recommendations: string[]
}

export interface DistractorRow {
  answer: string
  count: number
  percentage: number
  is_correct_option: boolean
}

export interface QuestionAnalytics {
  question_id: string
  assignment_id: string
  position: number
  prompt: string
  response_count: number
  correct_count: number
  correct_rate: number | null
  difficulty_index: number | null
  difficulty_label: string
  discrimination_index: number | null
  average_response_time: number | null
  omission_rate: number | null
  average_awarded_score: number | null
  distractors: DistractorRow[]
  curriculum_skill_codes: string[]
  ct_pillar_codes: string[]
}

export interface AssignmentAnalytics {
  assignment_id: string
  assignment_title: string
  participant_count: number
  attempt_count: number
  completion_rate: number
  average_percentage: number | null
  median_percentage: number | null
  average_time_seconds: number | null
  questions: QuestionAnalytics[]
  trend: TrendPoint[]
  data_quality_notes: string[]
}

export interface StudentOwnProgress {
  student_id: string
  average_percentage: number | null
  completed_activities: number
  trend: TrendPoint[]
  strengths: SkillMetric[]
  development_areas: SkillMetric[]
  next_steps: string[]
}
