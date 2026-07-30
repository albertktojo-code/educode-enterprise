export type StudioCreationMode = 'quick' | 'advanced'
export type StudioMaterialType =
  | 'comic'
  | 'quiz'
  | 'exercise'
  | 'activity'
  | 'game'
  | 'lesson_plan'
  | 'teaching_sequence'
  | 'answer_key'
  | 'teacher_guide'

export interface ArtDirectionPreset {
  id?: string | null
  code: string
  name: string
  category: string
  description: string
  preview_config: Record<string, unknown>
  visual_rules: Record<string, unknown>
  age_groups: string[]
  is_system: boolean
  is_active: boolean
}

export interface StudioTemplate {
  code: string
  name: string
  description: string
  outputs: StudioMaterialType[]
  story_pages: number
}

export interface PagePlanItem {
  page_number: number
  role: string
  panel_count: number
  layout_template: string
  narrative_function: string
}

export interface TeacherStudioDraft {
  id: string
  organization_id: string
  created_by_user_id: string
  generation_project_id?: string | null
  rag_context_id?: string | null
  title: string
  creation_mode: StudioCreationMode
  primary_material: StudioMaterialType
  subject_name: string
  school_year: string
  topic: string
  objective: string
  current_step: number
  wizard_data: Record<string, unknown>
  selected_outputs: StudioMaterialType[]
  page_plan: PagePlanItem[]
  art_direction: Record<string, unknown>
  accessibility_options: string[]
  status: string
  created_at: string
  updated_at: string
}

export interface PackageMaterial {
  id: string
  material_type: StudioMaterialType
  title: string
  content: Record<string, unknown>
  status: string
  position: number
  created_at: string
}

export interface PublicationPreparation {
  id: string
  readiness: string
  checklist: Array<Record<string, unknown>>
  manifest: Record<string, unknown>
  prepared_at: string
}

export interface PedagogicalPackage {
  id: string
  organization_id: string
  draft_id: string
  generation_project_id?: string | null
  comic_id?: string | null
  created_by_user_id: string
  created_by_name_snapshot: string
  title: string
  outputs: StudioMaterialType[]
  shared_context: Record<string, unknown>
  art_direction_snapshot: Record<string, unknown>
  status: string
  preparation_report: Record<string, unknown>
  created_at: string
  updated_at: string
  materials: PackageMaterial[]
  publication_preparations: PublicationPreparation[]
}
