import { api } from "../../lib/api";
import type {
  AccessibleVersionPreview,
  AccessibleVersionRecord,
  GraduatedHint,
  ProgressionRule,
  FeedbackResult,
  IndividualDifficultyResult,
  ObservedDifficultyResult,
  SpacedReviewResult,
} from "./types";

export const adaptiveEvolutionApi = {
  health: () => api<{ status: string; module: string; sprint: string }>("/adaptive-evolution/health"),
  createHint: (payload: Record<string, unknown>) => api.post<GraduatedHint>("/adaptive-evolution/hints", payload),
  listHints: (resourceType: string, resourceId: string, questionId?: string) => {
    const params = new URLSearchParams({ resource_type: resourceType, resource_id: resourceId });
    if (questionId) params.set("question_id", questionId);
    return api.get<GraduatedHint[]>(`/adaptive-evolution/hints?${params.toString()}`);
  },
  calculateReview: (payload: Record<string, unknown>) =>
    api.post<SpacedReviewResult>("/adaptive-evolution/reviews/calculate-next", payload),
  adaptFeedback: (payload: Record<string, unknown>) =>
    api.post<FeedbackResult>("/adaptive-evolution/feedback/adapt", payload),
  calculateIndividualDifficulty: (payload: Record<string, unknown>) =>
    api.post<IndividualDifficultyResult>("/adaptive-evolution/difficulty/individual", payload),
  calculateObservedDifficulty: (payload: Record<string, unknown>) =>
    api.post<ObservedDifficultyResult>("/adaptive-evolution/difficulty/observed", payload),
  createProgressionRule: (payload: Record<string, unknown>) =>
    api.post<ProgressionRule>("/adaptive-evolution/progression-rules", payload),
  listProgressionRules: () => api.get<ProgressionRule[]>("/adaptive-evolution/progression-rules"),
  publishProgressionRule: (ruleId: string) =>
    api.post<ProgressionRule>(`/adaptive-evolution/progression-rules/${ruleId}/publish`),
  previewAccessibleVersion: (payload: Record<string, unknown>) =>
    api.post<AccessibleVersionPreview>("/adaptive-evolution/accessibility/preview", payload),
  generateAccessibleVersion: (payload: Record<string, unknown>) =>
    api.post<AccessibleVersionRecord>("/adaptive-evolution/accessible-versions/generate", payload),
};
