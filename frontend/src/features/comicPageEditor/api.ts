import { api } from "../../lib/api";
import type {
  ActivityFeedbackProfile,
  BubbleConflict,
  BubbleLayer,
  ComicPage,
  EditorialComment,
  HQActivity,
  HQMonitoringSnapshot,
  HQLearningAnalyticsSnapshot,
  ComicPanel,
  ContinuityIssue,
  ContinuityRow,
  CoverComposition,
  CoverDraft,
  CoverTextLayer,
  EditorSnapshot,
  LayoutTemplate,
  PanelRect,
  PreservationOption,
  ProductivityAnalysis,
  StoryPlan,
} from "./types";

const BASE = "/comic-page-editor";

interface LayoutRaw {
  id: string;
  code: string;
  name: string;
  description: string;
  version: string;
  panel_count: number;
  orientation: "PORTRAIT" | "LANDSCAPE" | "SQUARE";
  category: string;
  grid_definition: {
    panels: PanelRect[];
    gutter: number;
    page_margin: number;
  };
  preview_metadata?: Record<string, unknown>;
  is_favorite?: boolean;
}

interface PageRaw {
  id: string;
  comic_project_id: string;
  layout_template_id?: string | null;
  page_number: number;
  page_type:
    | "COVER"
    | "STORY"
    | "ACTIVITY"
    | "ANSWER_KEY"
    | "BACK_COVER";
  title?: string | null;
  status: string;
  page_width: number;
  page_height: number;
  background_settings: Record<string, unknown>;
  accessibility_settings: Record<string, unknown>;
  content_layers: Array<{
    id: string;
    layer_type: CoverTextLayer["layerType"];
    content: string;
    x: number;
    y: number;
    width: number;
    height: number;
    style: Record<string, unknown>;
    visible: boolean;
  }>;
  preservation_settings: Record<string, unknown>;
  continuity_metadata: Record<string, string>;
  cover_generation: Record<string, unknown>;
  revision_number: number;
}

interface PanelRaw {
  id: string;
  page_id: string;
  panel_order: number;
  shape: ComicPanel["shape"];
  x: number;
  y: number;
  width: number;
  height: number;
  aspect_ratio: string;
  scene_summary: string;
  visual_prompt: string;
  generation_status: string;
  locked_elements: string[];
  pedagogical_metadata?: Record<string, unknown>;
  accessibility_metadata?: Record<string, unknown>;
}

interface StoryPlanRaw {
  exists: boolean;
  id?: string;
  comic_project_id: string;
  source_mode: StoryPlan["sourceMode"];
  total_pages: number;
  narrative_pacing: StoryPlan["narrativePacing"];
  distribution_mode: StoryPlan["distributionMode"];
  short_summary: string;
  full_script: string;
  page_plan: Array<Record<string, unknown>>;
  continuity_constraints: Record<string, unknown>;
  generation_instructions: Record<string, unknown>;
  generation_status: string;
  ai_generation_request_id?: string | null;
  content_hash?: string;
  revision_number: number;
}

interface CoverRaw {
  id: string;
  comic_project_id: string;
  composition_code: string;
  title: string;
  subtitle: string;
  author: string;
  school: string;
  classroom: string;
  discipline: string;
  theme: string;
  school_year: string;
  background_asset_reference?: string | null;
  focal_point: { x: number; y: number };
  scale: number;
  bleed_enabled: boolean;
  safe_area_enabled: boolean;
  spine_enabled: boolean;
  content_layers: PageRaw["content_layers"];
  preservation_settings: Record<string, unknown>;
  continuity_metadata: Record<string, string>;
  accessibility_settings: Record<string, unknown>;
  cover_generation: Record<string, unknown>;
  revision_number: number;
}

interface ActivityFeedbackProfileRaw {
  id: string;
  activity_binding_id: string;
  rubric_id?: string | null;
  rubric_version_id?: string | null;
  correction_mode: ActivityFeedbackProfile["correctionMode"];
  feedback_templates?: Record<string, unknown>;
  graduated_hints?: Array<Record<string, unknown>>;
  common_errors?: Array<Record<string, unknown>>;
  review_rules?: Record<string, unknown>;
  appeal_enabled: boolean;
  status: string;
}

interface HQActivityRaw {
  id: string;
  activity_page_id: string;
  source_page_id?: string | null;
  source_panel_id?: string | null;
  question_id?: string | null;
  question_version_id?: string | null;
  publication_id?: string | null;
  activity_type: string;
  title: string;
  instructions: string;
  activity_payload?: Record<string, unknown>;
  answer_key?: Record<string, unknown>;
  pedagogical_links?: Record<string, unknown>;
  accessibility?: Record<string, unknown>;
  difficulty: string;
  status: string;
  display_order: number;
  max_score: number;
  teacher_review_required: boolean;
}

interface BubbleLayerRaw {
  id: string;
  panel_id: string;
  layer_type: BubbleLayer["layerType"];
  speaker_name?: string | null;
  content: string;
  x: number;
  y: number;
  width: number;
  height: number;
  style?: Record<string, unknown>;
  reading_order: number;
  bubble_metadata?: Record<string, unknown>;
  accessibility_metadata?: Record<string, unknown>;
  review_status: string;
  linked_character_id?: string | null;
}

interface BubbleConflictRaw {
  code: string;
  severity: BubbleConflict["severity"];
  layer_id: string;
  other_layer_id?: string;
  message: string;
}

interface EditorialCommentRaw {
  id: string;
  project_id: string;
  target_type: EditorialComment["targetType"];
  target_id: string;
  content: string;
  status: EditorialComment["status"];
  priority: EditorialComment["priority"];
  created_by_user_id: string;
  resolved_by_user_id?: string | null;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
}

function mapLayout(item: LayoutRaw): LayoutTemplate {
  return {
    id: item.id,
    code: item.code,
    name: item.name,
    description: item.description,
    version: item.version,
    panelCount: item.panel_count,
    orientation: item.orientation,
    category: item.category,
    gridDefinition: {
      panels: item.grid_definition.panels,
      gutter: item.grid_definition.gutter,
      pageMargin: item.grid_definition.page_margin,
    },
    previewMetadata: item.preview_metadata,
    isFavorite: item.is_favorite,
  };
}

function mapPanel(item: PanelRaw): ComicPanel {
  return {
    id: item.id,
    panelOrder: item.panel_order,
    shape: item.shape,
    x: item.x,
    y: item.y,
    width: item.width,
    height: item.height,
    aspectRatio: item.aspect_ratio,
    sceneSummary: item.scene_summary,
    visualPrompt: item.visual_prompt,
    generationStatus: item.generation_status,
    lockedElements: item.locked_elements,
    pedagogicalMetadata: item.pedagogical_metadata,
    accessibilityMetadata: item.accessibility_metadata,
  };
}

function mapLayers(
  rows: PageRaw["content_layers"],
): CoverTextLayer[] {
  return rows.map((item) => ({
    id: item.id,
    layerType: item.layer_type,
    content: item.content,
    x: item.x,
    y: item.y,
    width: item.width,
    height: item.height,
    style: item.style,
    visible: item.visible,
  }));
}

function mapStoryPlan(item: StoryPlanRaw): StoryPlan {
  return {
    exists: item.exists,
    id: item.id,
    comicProjectId: item.comic_project_id,
    sourceMode: item.source_mode,
    totalPages: item.total_pages,
    narrativePacing: item.narrative_pacing,
    distributionMode: item.distribution_mode,
    shortSummary: item.short_summary,
    fullScript: item.full_script,
    pagePlan: item.page_plan,
    continuityConstraints: item.continuity_constraints,
    generationInstructions: item.generation_instructions,
    generationStatus: item.generation_status,
    aiGenerationRequestId: item.ai_generation_request_id,
    contentHash: item.content_hash,
    revisionNumber: item.revision_number,
  };
}

function mapCover(item: CoverRaw): CoverDraft {
  return {
    id: item.id,
    compositionCode: item.composition_code,
    title: item.title,
    subtitle: item.subtitle,
    author: item.author,
    school: item.school,
    classroom: item.classroom,
    discipline: item.discipline,
    theme: item.theme,
    schoolYear: item.school_year,
    backgroundAssetReference:
      item.background_asset_reference,
    focalPoint: item.focal_point,
    scale: item.scale,
    bleedEnabled: item.bleed_enabled,
    safeAreaEnabled: item.safe_area_enabled,
    spineEnabled: item.spine_enabled,
    contentLayers: mapLayers(item.content_layers),
    preservationSettings: item.preservation_settings,
    continuityMetadata: item.continuity_metadata,
    accessibilitySettings: item.accessibility_settings,
    coverGeneration: item.cover_generation,
    revisionNumber: item.revision_number,
  };
}

function coverBody(item: CoverDraft) {
  return {
    composition_code: item.compositionCode,
    title: item.title,
    subtitle: item.subtitle,
    author: item.author,
    school: item.school,
    classroom: item.classroom,
    discipline: item.discipline,
    theme: item.theme,
    school_year: item.schoolYear,
    background_asset_reference:
      item.backgroundAssetReference,
    focal_point: item.focalPoint,
    scale: item.scale,
    bleed_enabled: item.bleedEnabled,
    safe_area_enabled: item.safeAreaEnabled,
    spine_enabled: item.spineEnabled,
    content_layers: item.contentLayers.map((layer) => ({
      id: layer.id,
      layer_type: layer.layerType,
      content: layer.content,
      x: layer.x,
      y: layer.y,
      width: layer.width,
      height: layer.height,
      style: layer.style,
      visible: layer.visible,
    })),
    preservation_settings: item.preservationSettings,
    continuity_metadata: item.continuityMetadata,
    accessibility_settings: item.accessibilitySettings,
  };
}

export const comicPageEditorApi = {
  listLayouts: async (): Promise<LayoutTemplate[]> =>
    (await api.get<LayoutRaw[]>(`${BASE}/layouts`)).map(mapLayout),

  listPages: async (projectId: string): Promise<ComicPage[]> => {
    const pages = await api.get<PageRaw[]>(
      `${BASE}/projects/${projectId}/pages`,
    );
    return Promise.all(
      pages.map(async (page) => ({
        id: page.id,
        pageNumber: page.page_number,
        pageType: page.page_type,
        title: page.title ?? undefined,
        status: page.status,
        pageWidth: page.page_width,
        pageHeight: page.page_height,
        layoutTemplateId: page.layout_template_id,
        backgroundSettings: page.background_settings,
        accessibilitySettings: page.accessibility_settings,
        contentLayers: mapLayers(page.content_layers),
        preservationSettings: page.preservation_settings,
        continuityMetadata: page.continuity_metadata,
        coverGeneration: page.cover_generation,
        revisionNumber: page.revision_number,
        panels:
          page.page_type === "STORY"
            ? (
                await api.get<PanelRaw[]>(
                  `${BASE}/pages/${page.id}/panels`,
                )
              ).map(mapPanel)
            : [],
      })),
    );
  },

  getStoryPlan: async (projectId: string): Promise<StoryPlan> =>
    mapStoryPlan(
      await api.get<StoryPlanRaw>(
        `${BASE}/projects/${projectId}/story-plan`,
      ),
    ),

  saveStoryPlan: async (
    projectId: string,
    plan: StoryPlan,
  ): Promise<StoryPlan> =>
    mapStoryPlan(
      await api.put<StoryPlanRaw>(
        `${BASE}/projects/${projectId}/story-plan`,
        {
          source_mode: plan.sourceMode,
          total_pages: plan.totalPages,
          narrative_pacing: plan.narrativePacing,
          distribution_mode: plan.distributionMode,
          short_summary: plan.shortSummary,
          full_script: plan.fullScript,
          continuity_constraints: plan.continuityConstraints,
          generation_instructions: plan.generationInstructions,
        },
      ),
    ),

  generateStory: async (
    projectId: string,
    plan: StoryPlan,
  ) => {
    const response = await api.post<{
      story_plan: StoryPlanRaw;
      ai_request_id: string;
      ai_status: string;
      message: string;
    }>(`${BASE}/projects/${projectId}/story-plan/generate`, {
      total_pages: plan.totalPages,
      narrative_pacing: plan.narrativePacing,
      distribution_mode:
        plan.distributionMode === "MANUAL"
          ? "ASSISTED"
          : plan.distributionMode,
      short_summary: plan.shortSummary,
      continuity_constraints: plan.continuityConstraints,
      generation_instructions: plan.generationInstructions,
    });
    return {
      storyPlan: mapStoryPlan(response.story_plan),
      aiRequestId: response.ai_request_id,
      aiStatus: response.ai_status,
      message: response.message,
    };
  },

  distributeStory: async (
    projectId: string,
    options: {
      ensureTotalPages: boolean;
      preserveExistingSummaries: boolean;
      applyLayoutRecommendations: boolean;
    },
  ) => {
    const response = await api.post<{
      story_plan: StoryPlanRaw;
      pages: number;
      panels: number;
    }>(`${BASE}/projects/${projectId}/story-plan/distribute`, {
      ensure_total_pages: options.ensureTotalPages,
      preserve_existing_summaries:
        options.preserveExistingSummaries,
      apply_layout_recommendations:
        options.applyLayoutRecommendations,
    });
    return {
      storyPlan: mapStoryPlan(response.story_plan),
      pages: response.pages,
      panels: response.panels,
    };
  },

  preservationOptions: () =>
    api.get<PreservationOption[]>(`${BASE}/preservation-options`),

  coverCompositions: () =>
    api.get<CoverComposition[]>(`${BASE}/cover-compositions`),

  getCover: async (projectId: string) =>
    mapCover(
      await api.get<CoverRaw>(
        `${BASE}/projects/${projectId}/cover`,
      ),
    ),

  saveCover: async (
    projectId: string,
    cover: CoverDraft,
  ): Promise<CoverDraft> =>
    mapCover(
      await api.put<CoverRaw>(
        `${BASE}/projects/${projectId}/cover`,
        coverBody(cover),
      ),
    ),

  generateCover: async (
    projectId: string,
    options: {
      compositionCode: string;
      variationCount: number;
      additionalInstructions: string;
    },
  ) => {
    const result = await api.post<{
      cover: CoverRaw;
      ai_request_id: string;
      status: string;
      message: string;
    }>(`${BASE}/projects/${projectId}/cover/generate`, {
      composition_code: options.compositionCode,
      variation_count: options.variationCount,
      additional_instructions:
        options.additionalInstructions,
    });
    return {
      cover: mapCover(result.cover),
      requestId: result.ai_request_id,
      status: result.status,
      message: result.message,
    };
  },

  previewCoverResult: (
    projectId: string,
    resultId: string,
  ) =>
    api.get<{
      result_id: string;
      asset_reference: string;
      review_status: string;
      applied_to_module: boolean;
      requires_confirmation: boolean;
    }>(
      `${BASE}/projects/${projectId}/cover/results/${resultId}`,
    ),

  applyCoverResult: async (
    projectId: string,
    resultId: string,
  ): Promise<CoverDraft> =>
    mapCover(
      await api.post<CoverRaw>(
        `${BASE}/projects/${projectId}/cover/apply-result`,
        { result_id: resultId },
      ),
    ),

  createBackCover: (projectId: string) =>
    api.post(`${BASE}/projects/${projectId}/special-pages`, {
      page_type: "BACK_COVER",
      title: "Contracapa",
    }),

  continuityMap: async (projectId: string) => {
    const result = await api.get<{
      pages: Array<
        Omit<ContinuityRow, "pageId" | "pageNumber" | "pageType"> & {
          page_id: string;
          page_number: number;
          page_type: ContinuityRow["pageType"];
        }
      >;
      issues: ContinuityIssue[];
    }>(`${BASE}/projects/${projectId}/continuity-map`);
    return {
      pages: result.pages.map((row) => ({
        ...row,
        pageId: row.page_id,
        pageNumber: row.page_number,
        pageType: row.page_type,
      })),
      issues: result.issues,
    };
  },

  updateContinuity: (
    pageId: string,
    data: Record<string, string>,
  ) =>
    api.put(`${BASE}/pages/${pageId}/continuity`, data),

  applyPreservation: (
    pageId: string,
    data: {
      scope: "PANEL" | "PAGE" | "PROJECT";
      elements: string[];
      panelId?: string;
    },
  ) =>
    api.put(`${BASE}/pages/${pageId}/preservation`, {
      scope: data.scope,
      elements: data.elements,
      panel_id: data.panelId,
    }),

  applyLayout: async (
    pageId: string,
    layoutTemplateId: string,
  ): Promise<ComicPanel[]> =>
    (
      await api.post<PanelRaw[]>(
        `${BASE}/pages/${pageId}/layout`,
        {
          layout_template_id: layoutTemplateId,
          preserve_content: true,
        },
      )
    ).map(mapPanel),

  updatePanel: async (
    panelId: string,
    data: {
      sceneSummary?: string;
      visualPrompt?: string;
      lockedElements?: string[];
    },
  ): Promise<ComicPanel> =>
    mapPanel(
      await api.patch<PanelRaw>(`${BASE}/panels/${panelId}`, {
        scene_summary: data.sceneSummary,
        visual_prompt: data.visualPrompt,
        locked_elements: data.lockedElements,
      }),
    ),

  autosave: (
    projectId: string,
    data: {
      clientId: string;
      sequence: number;
      snapshot: EditorSnapshot;
      checksum: string;
    },
  ) =>
    api.post(`${BASE}/projects/${projectId}/autosave`, {
      client_id: data.clientId,
      sequence: data.sequence,
      payload: data.snapshot,
      checksum: data.checksum,
    }),

  latestAutosave: (
    projectId: string,
    clientId: string,
  ) =>
    api.get<{
      exists: boolean;
      sequence?: number;
      payload?: EditorSnapshot;
      checksum?: string;
      updated_at?: string;
    }>(
      `${BASE}/projects/${projectId}/autosave/latest?client_id=${encodeURIComponent(clientId)}`,
    ),

  createSnapshot: (
    projectId: string,
    label: string,
    revision: number,
    snapshot: EditorSnapshot,
  ) =>
    api.post(`${BASE}/projects/${projectId}/snapshots`, {
      label,
      snapshot_type: "MANUAL",
      revision_number: revision,
      data_snapshot: snapshot,
    }),

  listSnapshots: (projectId: string) =>
    api.get<
      Array<{
        id: string;
        label?: string;
        snapshot_type: string;
        revision_number: number;
        checksum: string;
        created_at: string;
      }>
    >(`${BASE}/projects/${projectId}/snapshots`),

  restoreSnapshot: (projectId: string, snapshotId: string) =>
    api.post<{
      snapshot_id: string;
      revision_number: number;
      checksum: string;
      payload: EditorSnapshot;
      requires_confirmation: boolean;
    }>(`${BASE}/projects/${projectId}/snapshots/restore`, {
      snapshot_id: snapshotId,
    }),







  generateLearningAnalytics: (
    deliveryId: string,
    data: Record<string, unknown> = { scope_type: "PUBLICATION" },
  ) =>
    api.post<HQLearningAnalyticsSnapshot>(
      `${BASE}/activity-deliveries/${deliveryId}/analytics/generate`,
      data,
    ),

  latestLearningAnalytics: (
    deliveryId: string,
  ) =>
    api.get<HQLearningAnalyticsSnapshot | null>(
      `${BASE}/activity-deliveries/${deliveryId}/analytics/latest`,
    ),

  createActivityDelivery: (projectId:string,data:Record<string,unknown>) =>
    api.post<{id:string;publication_id:string;status:string}>(`${BASE}/projects/${projectId}/activity-deliveries`,data),
  publishActivityDelivery: (deliveryId:string) =>
    api.post<Record<string,unknown>>(`${BASE}/activity-deliveries/${deliveryId}/publish`,{}),
  monitorActivityDelivery: (
    deliveryId: string,
    filters: {
      classroomId?: string;
      studentId?: string;
      status?: string;
      idleThresholdSeconds?: number;
    } = {},
  ) => {
    const query = new URLSearchParams();
    if (filters.classroomId) {
      query.set("classroom_id", filters.classroomId);
    }
    if (filters.studentId) {
      query.set("student_id", filters.studentId);
    }
    if (filters.status) query.set("status", filters.status);
    if (filters.idleThresholdSeconds) {
      query.set(
        "idle_threshold_seconds",
        String(filters.idleThresholdSeconds),
      );
    }
    const suffix = query.size ? `?${query.toString()}` : "";
    return api.get<HQMonitoringSnapshot>(
      `${BASE}/activity-deliveries/${deliveryId}/monitoring${suffix}`,
    );
  },

  teacherDeliveryAction: (
    sessionId: string,
    data: {
      action:
        | "PAUSE"
        | "RESUME"
        | "EXTEND"
        | "GRANT_ATTEMPT"
        | "SEND_MESSAGE"
        | "RELEASE_HINT"
        | "RELEASE_ANSWER_KEY";
      reason: string;
      extra_minutes?: number;
      additional_attempts?: number;
      message?: string;
      activity_id?: string;
      hint_level?: number;
    },
  ) =>
    api.post<Record<string, unknown>>(
      `/assessment-delivery/sessions/${sessionId}/actions`,
      data,
    ),

  getActivityFeedbackProfile: async (
    activityId: string,
  ): Promise<ActivityFeedbackProfile | null> => {
    const item = await api.get<ActivityFeedbackProfileRaw | null>(
      `${BASE}/activities/${activityId}/feedback-profile`,
    );
    if (!item) return null;
    return {
      id: item.id,
      activityBindingId: item.activity_binding_id,
      rubricId: item.rubric_id,
      rubricVersionId: item.rubric_version_id,
      correctionMode: item.correction_mode,
      feedbackTemplates: item.feedback_templates ?? {},
      graduatedHints: item.graduated_hints ?? [],
      commonErrors: item.common_errors ?? [],
      reviewRules: item.review_rules ?? {},
      appealEnabled: item.appeal_enabled,
      status: item.status,
    };
  },

  saveActivityFeedbackProfile: (
    activityId: string,
    data: Record<string, unknown>,
  ) =>
    api.put<Record<string, unknown>>(
      `${BASE}/activities/${activityId}/feedback-profile`,
      data,
    ),

  approveActivityFeedbackProfile: (
    activityId: string,
  ) =>
    api.post<Record<string, unknown>>(
      `${BASE}/activities/${activityId}/feedback-profile/approve`,
      {},
    ),

  simulateActivityCorrection: (
    activityId: string,
    response: Record<string, unknown>,
  ) =>
    api.post<{
      activity_id: string;
      result: Record<string, unknown>;
      feedback: Record<string, unknown>;
      correction_mode: string;
    }>(`${BASE}/activities/${activityId}/correction/simulate`, {
      response,
    }),

  activityTypes: () =>
    api.get<Array<{ code: string; label: string }>>(
      `${BASE}/activity-types`,
    ),

  listActivities: async (
    projectId: string,
  ): Promise<HQActivity[]> => {
    const items = await api.get<HQActivityRaw[]>(
      `${BASE}/projects/${projectId}/activities`,
    );
    return items.map((item) => ({
      id: item.id,
      activityPageId: item.activity_page_id,
      sourcePageId: item.source_page_id,
      sourcePanelId: item.source_panel_id,
      questionId: item.question_id,
      questionVersionId: item.question_version_id,
      publicationId: item.publication_id,
      activityType: item.activity_type,
      title: item.title,
      instructions: item.instructions,
      activityPayload: item.activity_payload ?? {},
      answerKey: item.answer_key ?? {},
      pedagogicalLinks: item.pedagogical_links ?? {},
      accessibility: item.accessibility ?? {},
      difficulty: item.difficulty,
      status: item.status,
      displayOrder: item.display_order,
      maxScore: item.max_score,
      teacherReviewRequired: item.teacher_review_required,
    }));
  },

  createActivity: (
    projectId: string,
    data: Record<string, unknown>,
  ) =>
    api.post<Record<string, unknown>>(
      `${BASE}/projects/${projectId}/activities`,
      data,
    ),

  approveActivity: (
    activityId: string,
  ) =>
    api.post<Record<string, unknown>>(
      `${BASE}/activities/${activityId}/approve`,
      {},
    ),

  buildWordSearch: (
    words: string[],
    size = 12,
  ) =>
    api.post<{
      size: number;
      grid: string[][];
      words: string[];
      placements: Array<Record<string, unknown>>;
    }>(`${BASE}/activities/word-search/build`, {
      words,
      size,
    }),

  validateCrossword: (
    entries: Array<{ answer: string; clue: string }>,
  ) =>
    api.post<{
      valid: boolean;
      errors: string[];
      entries: Array<Record<string, unknown>>;
      accessible_list: Array<Record<string, unknown>>;
    }>(`${BASE}/activities/crossword/validate`, {
      entries,
    }),

  ensureAnswerKeyPage: (
    projectId: string,
  ) =>
    api.post<Record<string, unknown>>(
      `${BASE}/projects/${projectId}/activities/answer-key-page`,
      {},
    ),

  bubbleTypes: () =>
    api.get<Array<{ code: string; label: string }>>(
      `${BASE}/bubble-types`,
    ),

  listPanelTextLayers: async (
    panelId: string,
  ): Promise<BubbleLayer[]> => {
    const items = await api.get<BubbleLayerRaw[]>(
      `${BASE}/panels/${panelId}/text-layers`,
    );
    return items.map((item) => ({
      id: item.id,
      panelId: item.panel_id,
      layerType: item.layer_type,
      speakerName: item.speaker_name,
      content: item.content,
      x: item.x,
      y: item.y,
      width: item.width,
      height: item.height,
      style: item.style ?? {},
      readingOrder: item.reading_order,
      bubbleMetadata: item.bubble_metadata ?? {},
      accessibilityMetadata: item.accessibility_metadata ?? {},
      reviewStatus: item.review_status,
      linkedCharacterId: item.linked_character_id,
    }));
  },

  updateTextLayer: (
    layerId: string,
    data: Record<string, unknown>,
  ) =>
    api.patch<Record<string, unknown>>(
      `${BASE}/text-layers/${layerId}`,
      data,
    ),

  analyzeBubbles: async (
    panelId: string,
  ): Promise<{
    status: "READY" | "WARNING" | "CRITICAL";
    conflicts: BubbleConflict[];
  }> => {
    const response = await api.post<{
      status: "READY" | "WARNING" | "CRITICAL";
      conflicts: BubbleConflictRaw[];
    }>(`${BASE}/panels/${panelId}/bubbles/analyze`, {});
    return {
      status: response.status,
      conflicts: response.conflicts.map((item) => ({
        code: item.code,
        severity: item.severity,
        layerId: item.layer_id,
        otherLayerId: item.other_layer_id,
        message: item.message,
      })),
    };
  },

  arrangeBubbles: (
    panelId: string,
    layerIds: string[],
  ) =>
    api.post(`${BASE}/panels/${panelId}/bubbles/arrange`, {
      layer_ids: layerIds,
    }),

  dialogueSuggestions: (
    content: string,
    schoolYear: string,
    tone = "natural",
  ) =>
    api.post<Array<{
      kind: string;
      label: string;
      suggestion: string;
    }>>(`${BASE}/dialogue/suggestions`, {
      content,
      school_year: schoolYear,
      tone,
    }),

  editorialComments: async (
    projectId: string,
  ): Promise<EditorialComment[]> => {
    const items = await api.get<EditorialCommentRaw[]>(
      `${BASE}/projects/${projectId}/editorial-comments`,
    );
    return items.map((item) => ({
      id: item.id,
      projectId: item.project_id,
      targetType: item.target_type,
      targetId: item.target_id,
      content: item.content,
      status: item.status,
      priority: item.priority,
      createdByUserId: item.created_by_user_id,
      resolvedByUserId: item.resolved_by_user_id,
      resolvedAt: item.resolved_at,
      createdAt: item.created_at,
      updatedAt: item.updated_at,
    }));
  },

  createEditorialComment: (
    projectId: string,
    data: {
      targetType: string;
      targetId: string;
      content: string;
      priority: string;
    },
  ) =>
    api.post(`${BASE}/projects/${projectId}/editorial-comments`, {
      target_type: data.targetType,
      target_id: data.targetId,
      content: data.content,
      priority: data.priority,
    }),

  updateEditorialCommentStatus: (
    commentId: string,
    status: string,
  ) =>
    api.patch(`${BASE}/editorial-comments/${commentId}/status`, {
      status,
    }),

  analyzeProductivity: async (
    projectId: string,
    expectedStoryPages: number,
  ): Promise<ProductivityAnalysis> => {
    const response = await api.post<{
      rhythm: {
        story_pages: number;
        expected_story_pages: number;
        average_panels_per_page: number;
        warning_count: number;
        status: "READY" | "WARNING" | "BLOCKED";
        warnings: Array<{
          code: string;
          severity: "LOW" | "MEDIUM" | "HIGH";
          message: string;
          page_number?: number;
        }>;
      };
      readability: {
        panels: Array<{
          panel_id: string;
          panel_order: number;
          word_count: number;
          density: number;
          status: "READY" | "WARNING" | "BLOCKED";
          warnings: Array<{
            code: string;
            severity: "LOW" | "MEDIUM" | "HIGH";
            message: string;
            page_number?: number;
          }>;
        }>;
        ready: number;
        warning: number;
        blocked: number;
      };
      publication_status:
        | "READY"
        | "READY_WITH_WARNINGS"
        | "BLOCKED";
    }>(`${BASE}/projects/${projectId}/productivity/analyze`, {
      expected_story_pages: expectedStoryPages,
    });
    const mapWarning = (item: {
      code: string;
      severity: "LOW" | "MEDIUM" | "HIGH";
      message: string;
      page_number?: number;
    }) => ({
      code: item.code,
      severity: item.severity,
      message: item.message,
      pageNumber: item.page_number,
    });
    return {
      rhythm: {
        storyPages: response.rhythm.story_pages,
        expectedStoryPages:
          response.rhythm.expected_story_pages,
        averagePanelsPerPage:
          response.rhythm.average_panels_per_page,
        warningCount: response.rhythm.warning_count,
        status: response.rhythm.status,
        warnings: response.rhythm.warnings.map(mapWarning),
      },
      readability: {
        panels: response.readability.panels.map((item) => ({
          panelId: item.panel_id,
          panelOrder: item.panel_order,
          wordCount: item.word_count,
          density: item.density,
          status: item.status,
          warnings: item.warnings.map(mapWarning),
        })),
        ready: response.readability.ready,
        warning: response.readability.warning,
        blocked: response.readability.blocked,
      },
      publicationStatus: response.publication_status,
    };
  },

  reorderStoryPages: (
    projectId: string,
    orderedStoryPageIds: string[],
    recalculateNarrative = false,
  ) =>
    api.post(
      `${BASE}/projects/${projectId}/pages/reorder-advanced`,
      {
        ordered_story_page_ids: orderedStoryPageIds,
        recalculate_narrative: recalculateNarrative,
      },
    ),

  reorderPanels: async (
    pageId: string,
    orderedPanelIds: string[],
  ): Promise<ComicPanel[]> =>
    (
      await api.post<PanelRaw[]>(
        `${BASE}/pages/${pageId}/panels/reorder`,
        { ordered_panel_ids: orderedPanelIds },
      )
    ).map(mapPanel),

  saveCurrentPageAsLayout: (
    pageId: string,
    data: {
      code: string;
      name: string;
      description: string;
      category: string;
    },
  ) =>
    api.post<LayoutRaw>(
      `${BASE}/pages/${pageId}/save-as-layout`,
      data,
    ).then(mapLayout),

  createGenerationJob: (projectId: string) =>
    api.post<{ id: string }>(
      `${BASE}/projects/${projectId}/generation-jobs`,
      {
        continue_in_background: true,
        generate_images: true,
        validate_bncc: true,
        validate_accessibility: true,
      },
    ),

  cancelGeneration: (jobId: string) =>
    api.post(`${BASE}/generation-jobs/${jobId}/cancel`),
};
