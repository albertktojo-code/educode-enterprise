export type AnimeProjectStatus =
  | 'draft'
  | 'in_review'
  | 'approved'
  | 'rendering'
  | 'ready'
  | 'rejected'
  | 'archived'

export interface AnimeScene {
  id: string
  organization_id: string
  project_id: string
  position: number
  title: string
  duration_ms: number
  visual_asset_file_id: string | null
  source_comic_page_id: string | null
  source_comic_panel_id: string | null
  screenplay_text: string
  visual_prompt: string
  negative_prompt: string
  camera_settings: Record<string, unknown>
  transition_settings: Record<string, unknown>
  continuity_data: Record<string, unknown>
  pedagogical_metadata: Record<string, unknown>
  status: string
  revision: number
  approved_by_user_id: string | null
  approved_at: string | null
  created_at: string
  updated_at: string
}

export interface AnimeAudioTrack {
  id: string
  project_id: string
  scene_id: string | null
  track_kind: 'dialogue' | 'narration' | 'music' | 'sfx' | 'audio_description'
  label: string
  language: string
  asset_file_id: string | null
  transcript: string
  speaker: string
  start_ms: number
  duration_ms: number | null
  trim_start_ms: number
  volume: number
  fade_in_ms: number
  fade_out_ms: number
  is_muted: boolean
  status: string
  created_at: string
  updated_at: string
}

export interface AnimeCaptionCue {
  id: string
  project_id: string
  scene_id: string | null
  language: string
  cue_order: number
  start_ms: number
  end_ms: number
  text: string
  speaker: string
  cue_kind: string
  accessibility_metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface AnimeRender {
  id: string
  project_id: string
  revision: number
  background_job_id: string | null
  output_asset_id: string | null
  output_asset_file_id: string | null
  status: 'queued' | 'processing' | 'in_review' | 'approved' | 'rejected' | 'failed'
  format: string
  video_codec: string
  audio_codec: string
  duration_ms: number | null
  render_settings: Record<string, unknown>
  manifest_checksum: string
  error_message: string
  review_decision: string
  review_notes: string
  reviewed_by_user_id: string | null
  reviewed_at: string | null
  created_at: string
  updated_at: string
}

export interface AnimeRenderJob {
  id: string
  status: string
  progress_percent: number
  current_step: string
  retry_count: number
  max_retries: number
  error_message: string
  queued_at: string | null
  started_at: string | null
  completed_at: string | null
}

export interface AnimeProjectSummary {
  id: string
  title: string
  synopsis: string
  style_preset_code: string
  aspect_ratio: string
  width: number
  height: number
  fps: number
  language: string
  status: AnimeProjectStatus
  revision: number
  created_at: string
  updated_at: string
}

export interface AnimeProject extends AnimeProjectSummary {
  organization_id: string
  generation_project_id: string | null
  rag_context_id: string | null
  teacher_studio_draft_id: string | null
  accessibility_options: Record<string, unknown>
  production_notes: Record<string, unknown>
  approved_by_user_id: string | null
  approved_at: string | null
  scenes: AnimeScene[]
  audio_tracks: AnimeAudioTrack[]
  captions: AnimeCaptionCue[]
  renders: AnimeRender[]
}

export interface AnimeMediaUpload {
  asset_id: string
  file_id: string
  file_name: string
  media_kind: 'image' | 'video' | 'audio'
  mime_type: string
  size_bytes: number
  download_path: string
}

export interface AnimeStoryboardImportResult {
  source_comic_id: string
  imported_count: number
  skipped_count: number
  total_duration_ms: number
  scenes: AnimeScene[]
}

export type AnimeMediaGenerationKind =
  | 'image'
  | 'animation'
  | 'voice'
  | 'lip_sync'
  | 'music'
  | 'sfx'

export interface AnimeMediaGeneration {
  id: string
  project_id: string
  scene_id: string | null
  kind: AnimeMediaGenerationKind
  status: string
  progress_percent: number
  current_step: string
  estimated_cost: number
  review_required: boolean
  review_decision: string
  output_asset_id: string | null
  output_asset_file_id: string | null
  provider: string
  error_message: string
  created_at: string
  completed_at: string | null
}
