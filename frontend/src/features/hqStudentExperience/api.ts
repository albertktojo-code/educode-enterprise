import { api } from "../../lib/api";

const BASE = "/comic-page-editor";
const DELIVERY_BASE = "/assessment-delivery";

export interface AssessmentSessionSummary {
  id: string;
  status: string;
  expires_at: string | null;
  remaining_seconds: number;
  accessibility: Record<string, unknown>;
}

export interface AssessmentSessionItem {
  id: string;
  session_id: string;
  question_version_id: string;
  position: number;
  original_position: number;
  option_order: string[];
  status: string;
  flagged_for_review: boolean;
}

export interface AssessmentSessionDetail {
  session: AssessmentSessionSummary & {
    publication_id: string;
    student_id: string;
  };
  items: AssessmentSessionItem[];
}

export interface StudentExperienceActivity {
  id: string;
  question_version_id: string | null;
  session_item_id: string | null;
  response_status: string;
  saved_response: Record<string, unknown>;
  activity_page_id: string;
  source_page_id: string | null;
  source_panel_id: string | null;
  activity_type: string;
  title: string;
  instructions: string;
  activity_payload: {
    options?: Array<{ id: string; text: string }>;
    selection_mode?: "SINGLE" | "MULTIPLE";
    left_items?: Array<{ id: string; text: string }>;
    right_items?: Array<{ id: string; text: string }>;
    items?: string[];
    blanks?: Array<{ id: string; label: string }>;
    entries?: Array<{
      id: string;
      clue: string;
      length: number;
    }>;
    grid?: string[][];
    words?: string[];
    [key: string]: unknown;
  };
  difficulty: string;
  max_score: number;
  pedagogical_links: Record<string, unknown>;
  accessibility: Record<string, unknown>;
  released_answer_key?: Record<string, unknown> | null;
}

export interface StudentExperiencePage {
  id: string;
  page_type: string;
  page_number: number;
  title?: string | null;
  background_settings?: {
    scene_summary?: unknown;
    theme?: unknown;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface StudentExperienceManifest {
  publication: {
    id: string;
    title: string;
    starts_at: string;
    ends_at: string;
    duration_minutes: number;
    allow_resume: boolean;
    navigation_mode: string;
    autosave_seconds: number;
  };
  delivery: {
    id: string;
    comic_project_id: string;
    release_id: string | null;
    delivery_mode: string;
    reader_required: boolean;
    release_answer_key: string;
  };
  assessment: {
    student_id: string;
    target_id: string;
    attempts_used: number;
    attempts_allowed: number;
    can_start: boolean;
    autosave_sequence: number;
    session: AssessmentSessionSummary | null;
  };
  teacher_support: {
    answer_key_released: boolean;
    updates: Array<{
      id: string;
      type: "SEND_MESSAGE" | "RELEASE_HINT" | "RELEASE_ANSWER_KEY";
      message: string | null;
      activity_id: string | null;
      hint_level: number | null;
      occurred_at: string;
    }>;
  };
  state: {
    id: string | null;
    current_stage: string;
    current_page_number: number;
    current_panel_number: number;
    current_activity_index: number;
    reading_progress: number;
    activity_progress: number;
    answered_count: number;
    total_activity_count: number;
    combined_progress: number;
    preferences: Record<string, unknown>;
    navigation_state: Record<string, unknown>;
    last_feedback: Record<string, unknown>;
    last_sequence: number;
    completed_at?: string | null;
  };
  pages: StudentExperiencePage[];
  activities: StudentExperienceActivity[];
}

export const studentExperienceApi = {
  manifest: (publicationId: string) =>
    api.get<StudentExperienceManifest>(
      `${BASE}/student-experience/publications/${publicationId}`,
    ),

  startSession: (
    publicationId: string,
    studentId: string,
    targetId: string,
  ) =>
    api.post<AssessmentSessionDetail>(`${DELIVERY_BASE}/sessions/start`, {
      publication_id: publicationId,
      student_id: studentId,
      target_id: targetId,
      device_context: { source: "HQ_STUDENT_EXPERIENCE" },
    }),

  autosaveResponse: (
    sessionId: string,
    sessionItemId: string,
    sequenceNumber: number,
    response: Record<string, unknown>,
  ) =>
    api.post<Record<string, unknown>>(
      `${DELIVERY_BASE}/sessions/${sessionId}/autosaves`,
      {
        session_item_id: sessionItemId,
        sequence_number: sequenceNumber,
        response,
        client_timestamp: new Date().toISOString(),
      },
    ),

  submitSession: (sessionId: string) =>
    api.post<AssessmentSessionSummary>(
      `${DELIVERY_BASE}/sessions/${sessionId}/submit`,
    ),

  requestHelp: (
    sessionId: string,
    metadata: Record<string, unknown>,
  ) =>
    api.post<{ status: string; integrity_status: string }>(
      `${DELIVERY_BASE}/sessions/${sessionId}/events`,
      {
        event_type: "STUDENT_HELP_REQUESTED",
        severity: "WARNING",
        source: "CLIENT",
        occurred_at: new Date().toISOString(),
        description: "Solicitação de apoio durante a experiência HQ.",
        metadata,
      },
    ),

  saveState: (
    publicationId: string,
    data: Record<string, unknown>,
  ) =>
    api.put<Record<string, unknown>>(
      `${BASE}/student-experience/publications/${publicationId}/state`,
      data,
    ),
};
