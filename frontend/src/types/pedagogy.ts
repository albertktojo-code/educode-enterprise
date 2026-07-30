export type SourceMode = 'document' | 'ai' | 'teacher_text' | 'hybrid'
export type SourceType =
  | 'document'
  | 'teacher_text'
  | 'ai_knowledge'
  | 'manual_instruction'
export type FidelityLevel = 'strict' | 'balanced' | 'creative'
export type IntegrationMode =
  | 'subject_focus'
  | 'computational_thinking_focus'
  | 'balanced'
export type DifficultyLevel =
  | 'introductory'
  | 'basic'
  | 'intermediate'
  | 'advanced'
export type PrivacyLevel = 'private' | 'team' | 'classroom' | 'organization'
export type GenerationStatus = 'draft' | 'in_review' | 'confirmed' | 'archived'
export type PillarRelevance = 'high' | 'medium' | 'complementary'
export type AssessmentDesign =
  | 'none'
  | 'diagnostic'
  | 'pre_post'
  | 'experimental_control'
  | 'formative'
  | 'summative'
  | 'tam'

export interface Pillar {
  id: string
  code: string
  name: string
  description: string
  pedagogical_examples?: string | null
  is_active: boolean
}

export interface GenerationPillar {
  id: string
  pillar_id: string
  code: string
  name: string
  relevance: PillarRelevance
  application_description?: string | null
  selected_by: string
}

export interface GenerationSource {
  id: string
  source_type: SourceType
  document_id?: string | null
  chapter_id?: string | null
  learning_unit_id?: string | null
  content_text?: string | null
  instructions?: string | null
  priority: number
  weight: number
  is_primary: boolean
  allow_ai_expansion: boolean
}

export interface PedagogyCatalog {
  pillars: Pillar[]
  standard_subject_codes: string[]
  material_types: string[]
  accessibility_options: string[]
  assessment_designs: string[]
}

export interface PillarRecommendation {
  pillar_id: string
  code: string
  name: string
  relevance: PillarRelevance
  justification: string
}

export interface LearningUnit {
  id: string
  organization_id: string
  chapter_id?: string | null
  subject_id?: string | null
  title: string
  description?: string | null
  start_page?: number | null
  end_page?: number | null
  school_year?: string | null
  difficulty_level: DifficultyLevel
  disciplinary_objective?: string | null
  is_confirmed: boolean
  position: number
  created_at: string
  updated_at: string
}

export interface GenerationProject {
  id: string
  organization_id: string
  project_id?: string | null
  created_by_user_id: string
  created_by_name_snapshot: string
  title: string
  source_mode: SourceMode
  subject_id?: string | null
  custom_subject_name?: string | null
  school_year?: string | null
  topic: string
  disciplinary_objective?: string | null
  computational_thinking_objective?: string | null
  teacher_text?: string | null
  teacher_instructions?: string | null
  allow_ai_expansion: boolean
  fidelity_level: FidelityLevel
  integration_mode: IntegrationMode
  difficulty_level: DifficultyLevel
  privacy_level: PrivacyLevel
  credit_name: string
  rights_confirmed: boolean
  bncc_skills: string[]
  desired_materials: string[]
  accessibility_options: string[]
  source_priority: string[]
  assessment_design: AssessmentDesign
  assessment_notes?: string | null
  cognitive_levels: string[]
  measurable_objectives: string[]
  evaluation_plan: Record<string, unknown>
  author_credit_settings: Record<string, unknown>
  status: GenerationStatus
  pillars: GenerationPillar[]
  sources: GenerationSource[]
  mock_proposal?: Record<string, unknown> | null
  created_at: string
  updated_at: string
}
