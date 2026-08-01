import { api } from "../../lib/api";
import type { Blueprint, ExternalInstrument, QuestionItem } from "./types";

const BASE = "/assessment-hub";

export const assessmentHubApi = {
  health: () => api.get<{ status: string; sprint: string }>(`${BASE}/health`),
  questions: () => api.get<QuestionItem[]>(`${BASE}/questions`),
  blueprints: () => api.get<Blueprint[]>(`${BASE}/blueprints`),
  instruments: () => api.get<ExternalInstrument[]>(`${BASE}/external-instruments`),
};
