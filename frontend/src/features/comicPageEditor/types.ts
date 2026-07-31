export type PanelShape =
  | "RECTANGLE"
  | "SQUARE"
  | "CIRCLE"
  | "ROUNDED";

export type StorySourceMode = "MANUAL" | "AI_SUMMARY";
export type NarrativePacing =
  | "SLOW"
  | "BALANCED"
  | "FAST"
  | "CINEMATIC";
export type DistributionMode =
  | "AUTOMATIC"
  | "ASSISTED"
  | "MANUAL";

export interface PanelRect {
  x: number;
  y: number;
  width: number;
  height: number;
  shape: PanelShape;
}

export interface LayoutTemplate {
  id: string;
  code: string;
  name: string;
  description: string;
  version: string;
  panelCount: number;
  orientation: "PORTRAIT" | "LANDSCAPE" | "SQUARE";
  category: string;
  gridDefinition: {
    panels: PanelRect[];
    gutter: number;
    pageMargin: number;
  };
  previewMetadata?: Record<string, unknown>;
  isFavorite?: boolean;
}

export interface ComicPanel extends PanelRect {
  id: string;
  panelOrder: number;
  aspectRatio: string;
  sceneSummary: string;
  visualPrompt: string;
  generationStatus: string;
  lockedElements: string[];
  pedagogicalMetadata?: Record<string, unknown>;
  accessibilityMetadata?: Record<string, unknown>;
}

export type ComicPageType =
  | "COVER"
  | "STORY"
  | "ACTIVITY"
  | "ANSWER_KEY"
  | "BACK_COVER";

export interface CoverTextLayer {
  id: string;
  layerType:
    | "TITLE"
    | "SUBTITLE"
    | "AUTHOR"
    | "SCHOOL"
    | "DISCIPLINE"
    | "THEME"
    | "BADGE"
    | "LOGO"
    | "CREDITS"
    | "SUMMARY";
  content: string;
  x: number;
  y: number;
  width: number;
  height: number;
  style: Record<string, unknown>;
  visible: boolean;
}

export interface ComicPage {
  id: string;
  pageNumber: number;
  pageType: ComicPageType;
  title?: string;
  status: string;
  pageWidth: number;
  pageHeight: number;
  layoutTemplateId?: string | null;
  backgroundSettings: Record<string, unknown>;
  accessibilitySettings: Record<string, unknown>;
  contentLayers: CoverTextLayer[];
  preservationSettings: Record<string, unknown>;
  continuityMetadata: Record<string, string>;
  coverGeneration: Record<string, unknown>;
  revisionNumber: number;
  panels: ComicPanel[];
}

export interface CoverComposition {
  code: string;
  label: string;
  description: string;
  title_zone: Record<string, number>;
  image_focus: Record<string, number>;
}

export interface CoverDraft {
  id?: string;
  compositionCode: string;
  title: string;
  subtitle: string;
  author: string;
  school: string;
  classroom: string;
  discipline: string;
  theme: string;
  schoolYear: string;
  backgroundAssetReference?: string | null;
  focalPoint: { x: number; y: number };
  scale: number;
  bleedEnabled: boolean;
  safeAreaEnabled: boolean;
  spineEnabled: boolean;
  contentLayers: CoverTextLayer[];
  preservationSettings: Record<string, unknown>;
  continuityMetadata: Record<string, string>;
  accessibilitySettings: Record<string, unknown>;
  coverGeneration: Record<string, unknown>;
  revisionNumber: number;
}

export interface ContinuityRow {
  pageId: string;
  pageNumber: number;
  pageType: ComicPageType;
  character?: string;
  outfit?: string;
  scenario?: string;
  important_object?: string;
  time_of_day?: string;
  emotion?: string;
  palette?: string;
}

export interface ContinuityIssue {
  type: string;
  field: string;
  from_page: number;
  to_page: number;
  from_value: string;
  to_value: string;
  message: string;
}

export interface EditorSnapshot {
  pages: ComicPage[];
  storyPlan: StoryPlan;
  cover: CoverDraft | null;
  selectedPageId: string;
  selectedPanelId: string;
  zoom: number;
}

export interface StoryPlan {
  exists: boolean;
  id?: string;
  comicProjectId: string;
  sourceMode: StorySourceMode;
  totalPages: number;
  narrativePacing: NarrativePacing;
  distributionMode: DistributionMode;
  shortSummary: string;
  fullScript: string;
  pagePlan: Array<Record<string, unknown>>;
  continuityConstraints: Record<string, unknown>;
  generationInstructions: Record<string, unknown>;
  generationStatus: string;
  aiGenerationRequestId?: string | null;
  contentHash?: string;
  revisionNumber: number;
}

export interface PreservationOption {
  key: string;
  label: string;
}

export interface GenerationStep {
  stepCode: string;
  title: string;
  playfulMessage: string;
  status:
    | "PENDING"
    | "RUNNING"
    | "COMPLETED"
    | "FAILED"
    | "SKIPPED";
  progressWeight: number;
}


export interface ProductivityWarning {
  code: string;
  severity: "LOW" | "MEDIUM" | "HIGH";
  message: string;
  pageNumber?: number;
}

export interface PanelReadabilityResult {
  panelId: string;
  panelOrder: number;
  wordCount: number;
  density: number;
  status: "READY" | "WARNING" | "BLOCKED";
  warnings: ProductivityWarning[];
}

export interface ProductivityAnalysis {
  rhythm: {
    storyPages: number;
    expectedStoryPages: number;
    averagePanelsPerPage: number;
    warningCount: number;
    status: "READY" | "WARNING" | "BLOCKED";
    warnings: ProductivityWarning[];
  };
  readability: {
    panels: PanelReadabilityResult[];
    ready: number;
    warning: number;
    blocked: number;
  };
  publicationStatus:
    | "READY"
    | "READY_WITH_WARNINGS"
    | "BLOCKED";
}


export interface BubbleLayer {
  id: string;
  panelId: string;
  layerType:
    | "SPEECH"
    | "THOUGHT"
    | "SHOUT"
    | "WHISPER"
    | "NARRATION"
    | "CAPTION"
    | "DEVICE"
    | "OFFSCREEN"
    | "SOUND_EFFECT";
  speakerName?: string | null;
  content: string;
  x: number;
  y: number;
  width: number;
  height: number;
  style: Record<string, unknown>;
  readingOrder: number;
  bubbleMetadata: Record<string, unknown>;
  accessibilityMetadata: Record<string, unknown>;
  reviewStatus: string;
  linkedCharacterId?: string | null;
}

export interface BubbleConflict {
  code: string;
  severity: "WARNING" | "CRITICAL";
  layerId: string;
  otherLayerId?: string;
  message: string;
}

export interface EditorialComment {
  id: string;
  projectId: string;
  targetType: "PROJECT" | "PAGE" | "PANEL" | "TEXT_LAYER" | "COVER";
  targetId: string;
  content: string;
  status: "OPEN" | "IN_REVIEW" | "RESOLVED" | "REOPENED";
  priority: "LOW" | "NORMAL" | "HIGH" | "CRITICAL";
  createdByUserId: string;
  resolvedByUserId?: string | null;
  resolvedAt?: string | null;
  createdAt: string;
  updatedAt: string;
}


export interface HQActivity {
  id: string;
  activityPageId: string;
  sourcePageId?: string | null;
  sourcePanelId?: string | null;
  questionId?: string | null;
  questionVersionId?: string | null;
  publicationId?: string | null;
  activityType: string;
  title: string;
  instructions: string;
  activityPayload: Record<string, unknown>;
  answerKey: Record<string, unknown>;
  pedagogicalLinks: Record<string, unknown>;
  accessibility: Record<string, unknown>;
  difficulty: string;
  status: string;
  displayOrder: number;
  maxScore: number;
  teacherReviewRequired: boolean;
}


export interface ActivityFeedbackProfile {
  id: string;
  activityBindingId: string;
  rubricId?: string | null;
  rubricVersionId?: string | null;
  correctionMode: "AUTOMATIC" | "RUBRIC" | "ASSISTED" | "HUMAN";
  feedbackTemplates: Record<string, unknown>;
  graduatedHints: Array<Record<string, unknown>>;
  commonErrors: Array<Record<string, unknown>>;
  reviewRules: Record<string, unknown>;
  appealEnabled: boolean;
  status: string;
}

export interface HQActivityDelivery {
  id:string;
  publicationId:string;
  status:string;
}

export type HQMonitoringPresence =
  | "NOT_STARTED"
  | "STARTED"
  | "READING"
  | "ANSWERING"
  | "PAUSED"
  | "COMPLETED";

export interface HQMonitoringStudent {
  student_id: string;
  student_name: string;
  classroom_ids: string[];
  classroom_names: string[];
  session_id: string | null;
  session_status: string | null;
  presence_status: HQMonitoringPresence;
  current_page_number: number | null;
  current_panel_number: number | null;
  current_activity_index: number | null;
  current_activity_id: string | null;
  current_activity_title: string | null;
  current_activity_difficulty: string | null;
  reading_progress: number;
  activity_progress: number;
  combined_progress: number;
  answered_count: number;
  total_activity_count: number;
  last_interaction_at: string | null;
  idle_seconds: number | null;
  is_idle: boolean;
  remaining_seconds: number | null;
  attempts_used: number;
  attempts_allowed: number;
  alerts: Array<{
    code: string;
    severity: "INFO" | "WARNING" | "HIGH";
    message: string;
  }>;
  support: {
    help_pending: boolean;
    next_hint: {
      level: number;
      label?: string;
      message: string;
    } | null;
    answer_key_released: boolean;
    last_teacher_update_at: string | null;
  };
}

export interface HQMonitoringSnapshot {
  delivery: {
    id: string;
    publication_id: string;
    title: string;
    status: string;
    starts_at: string;
    ends_at: string;
  };
  summary: {
    total_students: number;
    status_counts: Record<string, number>;
    started: number;
    active: number;
    completed: number;
    paused: number;
    attention: number;
    average_progress: number;
  };
  filters: {
    classrooms: Array<{ id: string; name: string }>;
  };
  students: HQMonitoringStudent[];
  monitoring: {
    transport: "AUTHENTICATED_POLLING";
    poll_after_seconds: number;
    idle_threshold_seconds: number;
    last_updated_at: string;
  };
  privacy: {
    answers_exposed: false;
    answer_keys_exposed: false;
    device_details_exposed: false;
    ranking_enabled: false;
    message: string;
  };
}

export interface HQLearningAnalyticsSnapshot {
  id: string;
  publication_id: string;
  metrics: {
    completion_rate?: number;
    reading_completion_rate?: number;
    activity_completion_rate?: number;
    resume_usage_rate?: number;
    abandonment_rate?: number;
    privacy_suppressed?: boolean;
    [key: string]: unknown;
  };
  skill_metrics: Array<{
    skill_type: string;
    skill_code: string;
    accuracy: number | null;
    evidence_count: number;
    activity_count: number;
  }>;
  page_metrics: Array<{
    page_id: string;
    page_number: number;
    title?: string | null;
    viewer_count: number;
    view_count: number;
    revisit_count: number;
    average_active_seconds: number;
  }>;
  activity_metrics: Array<{
    activity_id: string;
    question_version_id?: string | null;
    title: string;
    accuracy: number | null;
    attempt_count: number;
    scored_response_count: number;
    pending_review_count: number;
  }>;
  correlations: Array<Record<string, unknown>>;
  alerts: Array<{
    code: string;
    severity: string;
    message: string;
    learning_alert_id?: string;
    human_approval_required?: boolean;
  }>;
  generated_at: string;
}
