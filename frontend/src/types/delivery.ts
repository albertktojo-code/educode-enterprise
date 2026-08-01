export type AssignmentStatus =
  | 'draft'
  | 'scheduled'
  | 'published'
  | 'closed'
  | 'canceled'
  | 'archived'

export type AssignmentType =
  | 'reading'
  | 'reading_exercise'
  | 'activity'
  | 'quiz'
  | 'assessment'
  | 'pretest'
  | 'posttest'
  | 'reinforcement'
  | 'challenge'

export type QuestionType =
  | 'multiple_choice'
  | 'true_false'
  | 'short_text'
  | 'numeric'
  | 'multiple_select'
  | 'ordering'
  | 'matching'
  | 'essay'

export interface AssignmentSummary {
  id: string
  package_id: string
  title: string
  instructions: string
  assignment_type: AssignmentType
  status: AssignmentStatus
  available_from?: string | null
  due_at?: string | null
  time_limit_minutes?: number | null
  maximum_attempts: number
  maximum_score: number
  feedback_policy: string
  answer_key_policy: string
  published_at?: string | null
  created_at: string
  updated_at: string
}

export interface Recipient {
  id: string
  recipient_type: 'classroom' | 'user'
  classroom_id?: string | null
  user_id?: string | null
  status: string
  available_from_override?: string | null
  due_at_override?: string | null
  maximum_attempts_override?: number | null
  time_limit_minutes_override?: number | null
  accommodations: Record<string, unknown>
  assigned_at: string
}

export interface TeacherQuestion {
  id: string
  position: number
  question_type: QuestionType
  prompt: string
  options: Array<Record<string, unknown>>
  answer_key: Record<string, unknown>
  explanation: string
  points: number
  difficulty: string
  curriculum_skill_codes: string[]
  ct_pillar_codes: string[]
  source_references: Array<Record<string, unknown>>
  manual_grading: boolean
  shuffle_options: boolean
}

export interface AssignmentDetail extends AssignmentSummary {
  organization_id: string
  created_by_user_id: string
  created_by_name_snapshot: string
  material_snapshot: Record<string, unknown>
  snapshot_version: number
  minimum_score?: number | null
  randomize_questions: boolean
  randomize_options: boolean
  allow_pause: boolean
  allow_late_submission: boolean
  late_penalty_percent: number
  show_result_immediately: boolean
  results_released_at?: string | null
  settings: Record<string, unknown>
  recipients: Recipient[]
  questions: TeacherQuestion[]
}

export interface StudentProgressRow {
  student_id: string
  student_name: string
  student_email: string
  progress_status: string
  attempts_count: number
  best_score?: number | null
  best_percentage?: number | null
  last_activity_at?: string | null
  is_late: boolean
}

export interface QuestionProgressRow {
  question_id: string
  position: number
  prompt: string
  response_count: number
  automatically_graded_count: number
  correct_count: number
  correct_rate?: number | null
  average_score?: number | null
  most_common_wrong_answer?: Record<string, unknown> | null
}

export interface AssignmentProgress {
  assignment_id: string
  total_students: number
  not_started: number
  in_progress: number
  submitted: number
  graded: number
  average_percentage?: number | null
  completion_rate: number
  students: StudentProgressRow[]
  questions: QuestionProgressRow[]
}

export interface GradingQueueItem {
  answer_id: string
  attempt_id: string
  student_id: string
  student_name: string
  question_id: string
  question_prompt: string
  answer_payload: Record<string, unknown>
  maximum_points: number
  awarded_score: number
  teacher_feedback?: string | null
}

export interface StudentAssignmentCard {
  id: string
  title: string
  assignment_type: AssignmentType
  status: string
  available_from?: string | null
  due_at?: string | null
  time_limit_minutes?: number | null
  maximum_attempts: number
  attempts_used: number
  progress_status: string
  best_percentage?: number | null
  is_late: boolean
  accommodations: Record<string, unknown>
}

export interface StudentAssignmentDetail {
  id: string
  title: string
  instructions: string
  assignment_type: AssignmentType
  available_from?: string | null
  due_at?: string | null
  time_limit_minutes?: number | null
  maximum_attempts: number
  attempts_used: number
  maximum_score: number
  material: Record<string, unknown>
  progress_status: string
  can_start: boolean
  active_attempt_id?: string | null
  accommodations: Record<string, unknown>
}

export interface StudentQuestion {
  id: string
  position: number
  question_type: QuestionType
  prompt: string
  options: Array<{ id?: string; text?: string }>
  points: number
  difficulty: string
  curriculum_skill_codes: string[]
  ct_pillar_codes: string[]
}

export interface StudentAnswer {
  id: string
  question_id: string
  answer_payload: Record<string, unknown>
  is_correct?: boolean | null
  awarded_score: number
  response_time_seconds: number
  teacher_feedback?: string | null
  updated_at: string
}

export interface Attempt {
  id: string
  assignment_id: string
  student_id: string
  attempt_number: number
  status: string
  started_at: string
  last_saved_at?: string | null
  submitted_at?: string | null
  graded_at?: string | null
  score: number
  percentage: number
  time_spent_seconds: number
  teacher_feedback?: string | null
  grading_complete: boolean
  is_late: boolean
  late_penalty_applied: number
  time_limit_minutes_snapshot?: number | null
  maximum_attempts_snapshot: number
  randomization_state: Record<string, unknown>
  autosave_revision: number
  answers: StudentAnswer[]
}

export interface AttemptWorkspace {
  attempt: Attempt
  questions: StudentQuestion[]
  material: Record<string, unknown>
  feedback_policy: string
  answer_key_policy: string
}

export interface AttemptResult {
  attempt_id: string
  status: string
  score: number
  percentage: number
  maximum_score: number
  grading_complete: boolean
  result_available: boolean
  answer_key_available: boolean
  teacher_feedback?: string | null
  answers: Array<{
    question_id: string
    prompt: string
    answer_payload: Record<string, unknown>
    awarded_score: number
    is_correct?: boolean | null
    feedback?: string | null
    correct_answer?: Record<string, unknown> | null
    explanation?: string | null
  }>
}

export interface NotificationItem {
  id: string
  assignment_id?: string | null
  notification_type: string
  title: string
  message: string
  action_path?: string | null
  status: string
  created_at: string
  read_at?: string | null
}

export interface StudentPreview {
  assignment: StudentAssignmentDetail
  questions: StudentQuestion[]
  note: string
}
