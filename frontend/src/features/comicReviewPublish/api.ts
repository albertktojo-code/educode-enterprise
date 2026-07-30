import { api } from "../../lib/api";
import type { PublicationRelease, ReviewSession, ReviewThread } from "./types";

const BASE = "/comic-review-publish";

export const comicReviewPublishApi = {
  listSessions: (projectId?: string) =>
    api.get<ReviewSession[]>(`${BASE}/review-sessions${projectId ? `?comic_project_id=${projectId}` : ""}`),
  listThreads: (sessionId: string) =>
    api.get<ReviewThread[]>(`${BASE}/review-sessions/${sessionId}/threads`),
  listReleases: (projectId: string) =>
    api.get<PublicationRelease[]>(`${BASE}/projects/${projectId}/releases`),
  transitionSession: (sessionId: string, status: string) =>
    api.post(`${BASE}/review-sessions/${sessionId}/transition?target_status=${status}`),
  transitionRelease: (releaseId: string, status: string) =>
    api.post(`${BASE}/releases/${releaseId}/transition?target_status=${status}`),
};
