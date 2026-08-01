export type ReaderMode = "PAGE" | "PANEL" | "VERTICAL" | "FOCUS";

export interface ReaderPreferences {
  reader_mode: ReaderMode;
  font_scale: number;
  line_spacing: number;
  high_contrast: boolean;
  reduced_motion: boolean;
  screen_reader_mode: boolean;
  show_alt_text: boolean;
  auto_play_narration: boolean;
  caption_mode: "VISIBLE" | "ON_DEMAND" | "HIDDEN";
  focus_mode: boolean;
  narration_rate: number;
}

export interface ReaderRelease {
  id: string;
  comic_project_id: string;
  release_number: number;
  release_name: string;
  release_notes: string;
  status: string;
  published_at?: string | null;
  scheduled_at?: string | null;
}

export interface ReaderPanel {
  id?: string;
  panel_number?: number;
  reading_order?: number;
  scene_description?: string;
  narrative_goal?: string;
  alt_text?: string;
  audio_description?: string;
  image_asset_path?: string | null;
  image_url?: string | null;
  balloons?: Array<{
    id?: string;
    speaker_name_snapshot?: string;
    text?: string;
  }>;
}

export interface ReaderPage {
  id?: string;
  page_number?: number;
  title?: string;
  panels?: ReaderPanel[];
}

export interface ReaderManifest {
  release: ReaderRelease & { release_hash: string };
  snapshot: Record<string, unknown>;
  pages: ReaderPage[];
  accessibility: {
    total_panels: number;
    missing_alt_text: number;
    missing_audio_description: number;
    screen_reader_ready: boolean;
    narration_ready: boolean;
    accessible_versions: Array<Record<string, unknown>>;
    preflight_findings: Array<Record<string, unknown>>;
  };
  narrations: Array<{
    id: string;
    page_number?: number | null;
    panel_number?: number | null;
    source_type: string;
    language: string;
    transcript: string;
    audio_url?: string | null;
    duration_ms?: number | null;
    voice_settings: Record<string, unknown>;
  }>;
  glossary: Array<{
    id: string;
    term: string;
    definition: string;
    simplified_definition: string;
    page_number?: number | null;
    panel_number?: number | null;
    pronunciation: string;
    metadata: Record<string, unknown>;
  }>;
  assessment_links: Array<{
    id: string;
    question_bank_item_id: string;
    assignment_id?: string | null;
    assignment_title?: string | null;
    page_number: number;
    panel_number?: number | null;
    display_order: number;
    required: boolean;
    reveal_rule: string;
    question?: {
      title: string;
      item_type: string;
      prompt: string;
      options: Array<Record<string, unknown>>;
      points: number;
      difficulty: string;
      curriculum_skill_codes: string[];
      ct_pillar_codes: string[];
    } | null;
  }>;
}

export interface ReadingCheckpoint {
  release_id: string;
  page_number: number;
  panel_number: number;
  completed_panels: number;
  progress_percent: number;
  elapsed_seconds: number;
  last_sequence: number;
  reader_mode: ReaderMode;
  state: Record<string, unknown>;
  completed_at?: string | null;
}

export interface ReaderBookmark {
  id: string;
  page_number: number;
  panel_number?: number | null;
  label: string;
  note: string;
  created_at: string;
}

export interface PresentationState {
  id: string;
  release_id: string;
  presenter_user_id: string;
  title: string;
  join_code: string;
  status: "DRAFT" | "LIVE" | "PAUSED" | "ENDED" | "CANCELLED";
  current_page: number;
  current_panel: number;
  reveal_step: number;
  revision: number;
  allow_audience_join: boolean;
  sync_audience: boolean;
  reveal_mode: string;
  settings: Record<string, unknown>;
  presenter_note: string;
  started_at?: string | null;
  ended_at?: string | null;
  updated_at: string;
}
