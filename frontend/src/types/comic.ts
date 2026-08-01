export type ComicStatus = 'draft' | 'generating' | 'in_review' | 'approved' | 'archived'
export type PageFormat = 'a4' | 'square' | 'mobile' | 'instagram' | 'presentation_16_9' | 'custom'
export type PageOrientation = 'portrait' | 'landscape'
export type LayoutMode = 'template' | 'free' | 'recommended'
export type ReadingDirection = 'left_to_right' | 'right_to_left' | 'top_to_bottom'
export type PanelShape = 'rectangle' | 'square' | 'horizontal' | 'vertical' | 'circle' | 'oval' | 'panoramic' | 'custom'
export type PanelSize = 'small' | 'medium' | 'large' | 'full_page' | 'custom'
export type PanelStatus = 'draft' | 'needs_review' | 'validated' | 'locked'
export type BalloonType = 'speech' | 'thought' | 'shout' | 'whisper' | 'narration' | 'caption' | 'pedagogical'
export type GenerationScope = 'comic' | 'page' | 'panel' | 'balloons' | 'dialogue' | 'scene' | 'from_panel'
export type PreviewReviewStatus = 'not_reviewed' | 'in_review' | 'changes_requested' | 'approved' | 'locked'

export interface ComicBalloon {
  id: string
  panel_id: string
  sequence_number: number
  speaker_character_id?: string | null
  speaker_name_snapshot?: string | null
  balloon_type: BalloonType
  text: string
  emotion?: string | null
  responds_to_balloon_id?: string | null
  pedagogical_function?: string | null
  position_x: number
  position_y: number
  width: number
  height: number
  is_locked: boolean
  layer_config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface ComicPanel {
  id: string
  page_id: string
  panel_number: number
  reading_order: number
  shape: PanelShape
  size_category: PanelSize
  position_x: number
  position_y: number
  width: number
  height: number
  border_style: string
  border_width: number
  rotation: number
  z_index: number
  is_full_bleed: boolean
  clipping_mode: string
  narrative_goal: string
  pedagogical_goal: string
  ct_pillar_codes: string[]
  scene_description: string
  previous_panel_summary: string
  next_panel_hook: string
  initial_state: Record<string, unknown>
  final_state: Record<string, unknown>
  emotion: string
  plot_function: string
  continuity_notes: string[]
  status: PanelStatus
  locked_elements: string[]
  visual_prompt: Record<string, unknown>
  frozen_assets: Record<string, unknown>
  pacing: string
  image_asset_path?: string | null
  alt_text?: string | null
  audio_description?: string | null
  text_word_limit: number
  preview_review_status: PreviewReviewStatus
  preview_reviewed_by_user_id?: string | null
  preview_reviewed_at?: string | null
  preview_review_notes?: string | null
  created_at: string
  updated_at: string
  balloons: ComicBalloon[]
}

export interface ComicPage {
  id: string
  comic_id: string
  page_number: number
  title?: string | null
  page_format: PageFormat
  orientation: PageOrientation
  layout_mode: LayoutMode
  layout_template: string
  reading_direction: ReadingDirection
  panel_count: number
  width: number
  height: number
  margins: Record<string, unknown>
  notes?: string | null
  page_role: string
  background_config: Record<string, unknown>
  guides_config: Record<string, unknown>
  preview_review_status: PreviewReviewStatus
  preview_reviewed_by_user_id?: string | null
  preview_reviewed_at?: string | null
  preview_review_notes?: string | null
  created_at: string
  updated_at: string
  panels: ComicPanel[]
}

export interface ComicVersion {
  id: string
  comic_id: string
  version_number: number
  scope: string
  target_page_id?: string | null
  target_panel_id?: string | null
  target_balloon_id?: string | null
  change_description: string
  snapshot_json: Record<string, unknown>
  created_by_user_id: string
  created_at: string
}

export interface ComicGenerationRun {
  id: string
  comic_id: string
  requested_by_user_id: string
  scope: GenerationScope
  target_page_id?: string | null
  target_panel_id?: string | null
  status: string
  provider: string
  model: string
  configuration: Record<string, unknown>
  result_summary: Record<string, unknown>
  error_message?: string | null
  started_at?: string | null
  finished_at?: string | null
  created_at: string
}

export interface Comic {
  id: string
  organization_id: string
  generation_project_id: string
  rag_context_id: string
  created_by_user_id: string
  created_by_name_snapshot: string
  title: string
  synopsis: string
  status: ComicStatus
  current_version: number
  narrative_profile: Record<string, unknown>
  layout_preferences: Record<string, unknown>
  story_state: Record<string, unknown>
  continuity_score: number
  pedagogical_score: number
  notes?: string | null
  art_direction: Record<string, unknown>
  canvas_config: Record<string, unknown>
  publication_status: string
  review_state: Record<string, unknown>
  autosave_revision: number
  last_saved_at?: string | null
  edit_revision: number
  last_editor_user_id?: string | null
  last_editor_name_snapshot?: string | null
  last_editor_at?: string | null
  canvas_readiness_status: string
  canvas_readiness_checked_at?: string | null
  preview_status: PreviewReviewStatus
  preview_checked_at?: string | null
  created_at: string
  updated_at: string
  approved_at?: string | null
  pages: ComicPage[]
  versions: ComicVersion[]
  generation_runs: ComicGenerationRun[]
  review_comments: ComicReviewComment[]
  review_approvals: ComicReviewApproval[]
  regeneration_proposals: ComicRegenerationProposal[]
  edit_operations: ComicEditOperation[]
}

export interface ComicSummary {
  id: string
  generation_project_id: string
  rag_context_id: string
  title: string
  synopsis: string
  status: ComicStatus
  current_version: number
  page_count: number
  panel_count: number
  continuity_score: number
  pedagogical_score: number
  updated_at: string
}

export interface LayoutTemplate {
  code: string
  label: string
  panel_count: number
  description: string
  panels: Array<Record<string, unknown>>
}

export interface ContinuityIssue {
  severity: string
  code: string
  message: string
  page_id?: string | null
  panel_id?: string | null
  balloon_id?: string | null
}

export interface ContinuityReport {
  comic_id: string
  score: number
  is_valid: boolean
  issue_count: number
  issues: ContinuityIssue[]
}

export type ReviewSpecialty = 'narrative' | 'pedagogical' | 'visual' | 'accessibility'
export type ReviewDecision = 'pending' | 'approved' | 'changes_requested'
export type ReviewCommentStatus = 'open' | 'in_review' | 'resolved' | 'dismissed'
export type ProposalStatus = 'proposed' | 'accepted' | 'rejected' | 'superseded'

export interface ComicReviewComment {
  id: string
  organization_id: string
  comic_id: string
  page_id?: string | null
  panel_id?: string | null
  balloon_id?: string | null
  author_user_id: string
  author_name_snapshot: string
  specialty: ReviewSpecialty
  body: string
  anchor_x?: number | null
  anchor_y?: number | null
  priority: string
  status: ReviewCommentStatus
  created_at: string
  resolved_at?: string | null
}

export interface ComicReviewApproval {
  id: string
  comic_id: string
  specialty: ReviewSpecialty
  decision: ReviewDecision
  reviewer_user_id: string
  reviewer_name_snapshot: string
  notes?: string | null
  reviewed_at: string
}

export interface ComicRegenerationProposal {
  id: string
  comic_id: string
  requested_by_user_id: string
  scope: GenerationScope
  target_page_id?: string | null
  target_panel_id?: string | null
  label: string
  tone: string
  instruction?: string | null
  proposal_payload: Record<string, unknown>
  status: ProposalStatus
  created_at: string
  accepted_at?: string | null
}

export interface ComicEditOperation {
  id: string
  comic_id: string
  actor_user_id: string
  operation_type: string
  target_page_id?: string | null
  target_panel_id?: string | null
  target_balloon_id?: string | null
  status: 'applied' | 'undone' | 'redone'
  created_at: string
  reverted_at?: string | null
}

export interface NarrativeMapItem {
  page_number: number
  panel_id: string
  reading_order: number
  plot_function: string
  pacing: string
  emotion: string
  narrative_goal: string
  open_questions: string[]
  clues: string[]
  word_count: number
  over_text_limit: boolean
}

export interface NarrativeMap {
  comic_id: string
  items: NarrativeMapItem[]
  pacing_warnings: string[]
  unresolved_clues: string[]
}

export interface StabilityFinding {
  severity: string
  code: string
  message: string
  page_id?: string | null
  panel_id?: string | null
  balloon_id?: string | null
}

export interface PageDensity {
  page_id: string
  page_number: number
  panel_coverage_percent: number
  word_count: number
  density_score: number
  classification: string
}

export interface StabilityReport {
  comic_id: string
  score: number
  language_metrics: Record<string, number>
  page_densities: PageDensity[]
  findings: StabilityFinding[]
  generated_at: string
}

export interface CanvasChecklistItem {
  code: string
  label: string
  passed: boolean
  required: boolean
}

export interface CanvasReadiness {
  comic_id: string
  status: 'ready' | 'ready_with_warnings' | 'not_ready'
  continuity_score: number
  checklist: CanvasChecklistItem[]
  checked_at: string
}

export interface RegenerationPolicy {
  comic_id: string
  scope: GenerationScope
  affected_panel_ids: string[]
  mutable_elements: string[]
  locked_elements: string[]
  immutable_facts: string[]
  warnings: string[]
}
