import { api } from "../../lib/api";
import type { CanvasDocument, CanvasLayer, ExportPreset, PreflightFinding } from "./types";

const BASE = "/comic-layout-studio";

export const comicLayoutStudioApi = {
  getDocument: (documentId: string) => api.get<CanvasDocument>(`${BASE}/documents/${documentId}`),
  listLayers: (documentId: string) => api.get<CanvasLayer[]>(`${BASE}/documents/${documentId}/layers`),
  listPresets: () => api.get<ExportPreset[]>(`${BASE}/export-presets`),
  updateLayer: (layerId: string, payload: unknown) =>
    api.patch<CanvasLayer>(`${BASE}/layers/${layerId}`, payload),
  preflight: (documentId: string) =>
    api.post<{ valid: boolean; findings: PreflightFinding[] }>(
      `${BASE}/documents/${documentId}/preflight`,
      { output_format: "PDF", minimum_dpi: 150, persist_findings: true },
    ),
  createExport: (documentId: string, presetId?: string) =>
    api.post(`${BASE}/documents/${documentId}/export-jobs`, {
      preset_id: presetId,
      output_format: "PDF",
      run_preflight: true,
      allow_warnings: true,
    }),
};
