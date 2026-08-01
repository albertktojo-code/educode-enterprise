import type { PreviewReviewStatus } from './comic'

export interface StoryboardDialogue {
  balloon_id: string
  sequence_number: number
  speaker: string
  type: string
  text: string
  emotion?: string | null
}

export interface StoryboardScene {
  sequence_number: number
  page_id: string
  page_number: number
  page_role: string
  panel_id: string
  panel_number: number
  reading_order: number
  review_status: PreviewReviewStatus
  scene_summary: string
  narrative_goal: string
  pedagogical_goal: string
  ct_pillar_codes: string[]
  shot_type: string
  camera_direction?: unknown
  action: unknown
  emotion: string
  pacing: string
  plot_function: string
  previous_panel_summary: string
  next_panel_hook: string
  initial_state: Record<string, unknown>
  final_state: Record<string, unknown>
  transition: string
  estimated_duration_seconds: number
  dialogue: StoryboardDialogue[]
  image_asset_path?: string | null
  alt_text?: string | null
  audio_description?: string | null
}

export interface Storyboard {
  comic_id: string
  title: string
  version: number
  page_count: number
  scene_count: number
  estimated_duration_seconds: number
  emotional_arc: string[]
  plot_points: Array<{
    sequence_number: number
    page_number: number
    panel_number: number
    type: string
    summary: string
  }>
  scenes: StoryboardScene[]
}

export interface PreviewValidation {
  comic_id: string
  status: 'ready' | 'ready_with_warnings' | 'blocked'
  review_coverage_percent: number
  approved_pages: number
  total_pages: number
  approved_panels: number
  total_panels: number
  error_count: number
  warning_count: number
  findings: Array<{
    severity: 'error' | 'warning' | 'info'
    code: string
    message: string
    page_id?: string | null
    panel_id?: string | null
  }>
  checklist: Array<{ code: string; label: string; passed: boolean }>
}

export interface VersionComparison {
  from_version: number
  to_version: number
  top_level_changes: string[]
  page_summary: Record<string, number>
  changed_pages: Array<{
    page_id: string
    page_number?: number | null
    status: string
    panel_changes: Array<{
      panel_id: string
      status: string
      changed_fields: string[]
    }>
  }>
}

export interface StudentPreview {
  comic_id: string
  title: string
  version: number
  reading_direction: string
  pages: Array<Record<string, unknown>>
  accessibility: Record<string, unknown>
  is_simulation: boolean
}
