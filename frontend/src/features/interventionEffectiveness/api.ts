import { api, apiBlob } from "../../lib/api";
import type {
  EffectivenessDashboard,
  EffectivenessMetric,
  EffectivenessRefreshResult,
  EffectivenessWindow,
  EvaluationCheckpoint,
} from "./types";

const BASE = "/intervention-effectiveness";

function queryString(
  values: Record<string, string | boolean | undefined>,
): string {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      params.set(key, String(value));
    }
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

export const interventionEffectivenessApi = {
  windows: () => api.get<EffectivenessWindow[]>(`${BASE}/windows`),
  dashboard: (periodStart: string, periodEnd: string) =>
    api.get<EffectivenessDashboard>(
      `${BASE}/dashboard${queryString({
        period_start: periodStart,
        period_end: periodEnd,
      })}`,
    ),
  checkpoints: (options: {
    status?: string;
    windowCode?: string;
    dueOnly?: boolean;
  }) =>
    api.get<EvaluationCheckpoint[]>(
      `${BASE}/checkpoints${queryString({
        status: options.status,
        window_code: options.windowCode,
        due_only: options.dueOnly,
      })}`,
    ),
  metrics: (options: {
    periodStart: string;
    periodEnd: string;
    windowCode?: string;
    dimensionType?: string;
  }) =>
    api.get<EffectivenessMetric[]>(
      `${BASE}/metrics${queryString({
        period_start: options.periodStart,
        period_end: options.periodEnd,
        window_code: options.windowCode,
        dimension_type: options.dimensionType,
      })}`,
    ),
  refresh: (data: {
    period_start: string;
    period_end: string;
    evaluate_due: boolean;
    window_code?: string;
  }) =>
    api.post<EffectivenessRefreshResult>(`${BASE}/refresh`, data),
  evaluate: (
    checkpointId: string,
    data: {
      force: boolean;
      observed_progress_percent?: number;
      observed_score_percent?: number;
    },
  ) =>
    api.post<EvaluationCheckpoint>(
      `${BASE}/checkpoints/${checkpointId}/evaluate`,
      data,
    ),
  exportCsv: (
    periodStart: string,
    periodEnd: string,
    windowCode?: string,
  ) =>
    apiBlob(
      `${BASE}/export.csv${queryString({
        period_start: periodStart,
        period_end: periodEnd,
        window_code: windowCode,
      })}`,
    ),
};
