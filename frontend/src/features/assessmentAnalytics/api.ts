import { api } from "../../lib/api";

const BASE = "/assessment-analytics";

export const assessmentAnalyticsApi = {
  health: () => api.get<{ status: string; sprint: string }>(`${BASE}/health`),
  models: () => api.get<unknown[]>(`${BASE}/models`),
  runs: () => api.get<unknown[]>(`${BASE}/runs`),
  reports: () => api.get<unknown[]>(`${BASE}/reports`),
  simulateItem: (payload: unknown) => api.post(`${BASE}/simulate/item`, payload),
  simulateDistractors: (payload: unknown) => api.post(`${BASE}/simulate/distractors`, payload),
};
