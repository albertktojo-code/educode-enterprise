import { api } from "../../lib/api";
import type {
  InterventionAlert,
  InterventionDashboard,
  InterventionOutcome,
  InterventionProposal,
  InterventionTimelineEvent,
  LearningIntervention,
  StudentIntervention,
} from "./types";

const BASE = "/intervention-orchestration";

export const interventionOrchestrationApi = {
  dashboard: () => api.get<InterventionDashboard>(`${BASE}/dashboard`),
  alerts: () => api.get<InterventionAlert[]>(`${BASE}/alerts`),
  proposals: (status?: string) =>
    api.get<InterventionProposal[]>(
      `${BASE}/proposals${status ? `?status=${encodeURIComponent(status)}` : ""}`,
    ),
  interventions: (status?: string) =>
    api.get<LearningIntervention[]>(
      `${BASE}/interventions${status ? `?status=${encodeURIComponent(status)}` : ""}`,
    ),
  createProposal: (
    alertId: string,
    data: {
      use_ai: boolean;
      due_days: number;
      evaluation_days: number;
      teacher_note: string;
      target_mastery: number;
    },
  ) =>
    api.post<InterventionProposal>(
      `${BASE}/proposals/from-alert/${alertId}`,
      data,
    ),
  reviewProposal: (
    recommendationId: string,
    data: {
      decision: "approved" | "rejected";
      review_notes: string;
      due_days: number;
      evaluation_days: number;
      create_adaptive_path: boolean;
    },
  ) =>
    api.patch<{
      proposal: InterventionProposal;
      intervention?: LearningIntervention | null;
    }>(`${BASE}/proposals/${recommendationId}`, data),
  transition: (
    interventionId: string,
    targetStatus: "active" | "canceled",
    notes = "",
  ) =>
    api.post<LearningIntervention>(
      `${BASE}/interventions/${interventionId}/transition`,
      { target_status: targetStatus, notes },
    ),
  complete: (
    interventionId: string,
    data: {
      result_summary: string;
      teacher_notes: string;
      observed_progress_percent?: number;
      observed_score_percent?: number;
    },
  ) =>
    api.post<{
      intervention: LearningIntervention;
      outcome: InterventionOutcome;
    }>(`${BASE}/interventions/${interventionId}/complete`, data),
  timeline: (interventionId: string) =>
    api.get<InterventionTimelineEvent[]>(
      `${BASE}/interventions/${interventionId}/timeline`,
    ),
  myInterventions: () =>
    api.get<StudentIntervention[]>(`${BASE}/my-interventions`),
  acknowledge: (interventionId: string, note = "") =>
    api.post<{ acknowledged: boolean }>(
      `${BASE}/my-interventions/${interventionId}/acknowledge`,
      { note },
    ),
};
