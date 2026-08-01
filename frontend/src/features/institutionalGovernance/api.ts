import { api, apiBlob } from "../../lib/api";
import type {
  GovernanceAsset,
  GovernanceComparison,
  GovernanceDashboard,
  GovernanceIncident,
  GovernanceRefreshResult,
  GovernanceSnapshot,
} from "./types";

const BASE = "/institutional-governance";

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

export const institutionalGovernanceApi = {
  dashboard: () => api.get<GovernanceDashboard>(`${BASE}/dashboard`),
  bootstrap: () =>
    api.post<{ created: Record<string, number> }>(`${BASE}/bootstrap`, {
      include_adaptive_models: true,
      include_ai_models: true,
      include_prompt_templates: true,
      include_module_policies: true,
      include_intervention_types: true,
      include_evidence_rules: true,
    }),
  assets: (filters?: {
    status?: string;
    assetType?: string;
  }) =>
    api.get<GovernanceAsset[]>(
      `${BASE}/assets${queryString({
        status: filters?.status,
        asset_type: filters?.assetType,
      })}`,
    ),
  asset: (assetId: string) =>
    api.get<GovernanceAsset>(`${BASE}/assets/${assetId}`),
  createVersion: (assetId: string, changeSummary: string) =>
    api.post<GovernanceAsset>(`${BASE}/assets/${assetId}/version`, {
      change_summary: changeSummary,
    }),
  submit: (assetId: string) =>
    api.post<GovernanceAsset>(`${BASE}/assets/${assetId}/submit`, {}),
  review: (
    assetId: string,
    data: {
      review_stage: string;
      decision: "approved" | "rejected" | "changes_requested";
      scorecard: Record<string, unknown>;
      findings: Array<Record<string, unknown>>;
      required_actions: string[];
      comments: string;
    },
  ) =>
    api.post<{ asset: GovernanceAsset; review_id: string }>(
      `${BASE}/assets/${assetId}/reviews`,
      data,
    ),
  action: (
    assetId: string,
    action: "activate" | "suspend" | "reinstate" | "retire",
    reason: string,
  ) =>
    api.post<GovernanceAsset | { asset: GovernanceAsset }>(
      `${BASE}/assets/${assetId}/${action}`,
      { reason },
    ),
  compare: (leftId: string, rightId: string) =>
    api.get<GovernanceComparison>(
      `${BASE}/compare${queryString({
        left_id: leftId,
        right_id: rightId,
      })}`,
    ),
  refresh: (data: {
    period_start?: string;
    period_end?: string;
    open_incidents: boolean;
  }) =>
    api.post<GovernanceRefreshResult>(
      `${BASE}/monitoring/refresh`,
      data,
    ),
  snapshots: (breachedOnly = false) =>
    api.get<GovernanceSnapshot[]>(
      `${BASE}/monitoring/snapshots${queryString({
        breached_only: breachedOnly,
      })}`,
    ),
  incidents: (status?: string) =>
    api.get<GovernanceIncident[]>(
      `${BASE}/incidents${queryString({ status })}`,
    ),
  resolveIncident: (incidentId: string, resolutionSummary: string) =>
    api.post<GovernanceIncident>(
      `${BASE}/incidents/${incidentId}/resolve`,
      { resolution_summary: resolutionSummary },
    ),
  exportCsv: () => apiBlob(`${BASE}/export.csv`),
};
