import { api } from "../../lib/api";
import type { AssessmentPublication, AvailableAssessment, MonitoringSummary } from "./types";

const BASE = "/assessment-delivery";

export const assessmentDeliveryApi = {
  health: () => api.get<{ status: string; sprint: string }>(`${BASE}/health`),
  publications: () => api.get<AssessmentPublication[]>(`${BASE}/publications`),
  monitor: (publicationId: string) =>
    api.get<MonitoringSummary>(`${BASE}/monitor/publications/${publicationId}`),
  available: (studentId: string) =>
    api.get<AvailableAssessment[]>(`${BASE}/students/${studentId}/available`),
};
