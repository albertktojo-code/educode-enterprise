import { api } from "../../lib/api";
import type {
  AdaptiveModelRecord,
  ControlledExperimentRecord,
  MaterialEffectivenessResult,
  SimulationResult,
} from "./types";

export const adaptiveInsightsApi = {
  health: () => api.get<{ status: string; module: string; sprint: string }>("/adaptive-insights/health"),
  recommend: (payload: Record<string, unknown>) =>
    api.post("/adaptive-insights/recommendations/from-interventions", payload),
  effectiveness: (payload: Record<string, unknown>, persist = false) =>
    api.post<MaterialEffectivenessResult>(`/adaptive-insights/materials/effectiveness?persist=${persist}`, payload),
  createModel: (payload: Record<string, unknown>) =>
    api.post<AdaptiveModelRecord>("/adaptive-insights/models", payload),
  listModels: () => api.get<AdaptiveModelRecord[]>("/adaptive-insights/models"),
  publishModel: (id: string) => api.post<AdaptiveModelRecord>(`/adaptive-insights/models/${id}/publish`),
  simulate: (payload: Record<string, unknown>) =>
    api.post<SimulationResult>("/adaptive-insights/simulations", payload),
  createExperiment: (payload: Record<string, unknown>) =>
    api.post<ControlledExperimentRecord>("/adaptive-insights/experiments", payload),
  listExperiments: () => api.get<ControlledExperimentRecord[]>("/adaptive-insights/experiments"),
  dashboard: (payload: Record<string, unknown>) =>
    api.post("/adaptive-insights/institutional-paths/dashboard", payload),
};
