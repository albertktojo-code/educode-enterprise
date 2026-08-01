export type LayerType =
  | "PANEL"
  | "IMAGE"
  | "SPEECH_BALLOON"
  | "THOUGHT_BALLOON"
  | "CAPTION"
  | "NARRATION"
  | "SOUND_EFFECT"
  | "SHAPE"
  | "DECORATION"
  | "PEDAGOGICAL_BADGE";

export interface CanvasDocument {
  id: string;
  comicProjectId: string;
  pageId: string;
  name: string;
  pageWidth: number;
  pageHeight: number;
  dpi: number;
  bleedMm: number;
  safeMarginMm: number;
  gridSize: number;
  snapEnabled: boolean;
  rulersEnabled: boolean;
  showBleed: boolean;
  showSafeArea: boolean;
  revisionNumber: number;
}

export interface CanvasLayer {
  id: string;
  layerType: LayerType;
  name: string;
  zIndex: number;
  x: number;
  y: number;
  width: number;
  height: number;
  rotationDeg: number;
  opacity: number;
  visible: boolean;
  locked: boolean;
  shape: string;
  style: Record<string, unknown>;
  content: Record<string, unknown>;
  accessibilityMetadata: Record<string, unknown>;
}

export interface CanvasGuide {
  id: string;
  orientation: "HORIZONTAL" | "VERTICAL";
  position: number;
  guideType: string;
  visible: boolean;
  locked: boolean;
  label?: string;
}

export interface PreflightFinding {
  severity: "INFO" | "WARNING" | "ERROR";
  code: string;
  message: string;
  resourceType?: string;
  resourceId?: string;
}

export interface ExportPreset {
  id: string;
  code: string;
  name: string;
  outputFormat: string;
  pageSize: string;
  dpi: number;
  includeBleed: boolean;
  includeCropMarks: boolean;
}
