import { api, apiBlob } from "../../lib/api";
import type {
  AccessibilityMetric,
  ContentMetric,
  LearningMetric,
  ReaderAnalyticsEventInput,
  ReaderAnalyticsOverview,
} from "./types";

const BASE = "/comic-reader-analytics";

export const comicReaderAnalyticsApi = {
  events: (events: ReaderAnalyticsEventInput[]) =>
    api.post<{ accepted: number; duplicates: number }>(`${BASE}/events/batch`, {
      events: events.map((event) => ({
        ...event,
        client_event_id: crypto.randomUUID(),
        occurred_at: new Date().toISOString(),
      })),
    }),
  refresh: (data: {
    period_start: string;
    period_end: string;
    release_id?: string;
    classroom_id?: string;
    generate_alerts: boolean;
  }) => api.post<Record<string, unknown>>(`${BASE}/refresh`, data),
  overview: (start: string, end: string, releaseId?: string) => {
    const query = new URLSearchParams({ period_start: start, period_end: end });
    if (releaseId) query.set("release_id", releaseId);
    return api.get<ReaderAnalyticsOverview>(`${BASE}/overview?${query}`);
  },
  content: (releaseId: string, start: string, end: string) => {
    const query = new URLSearchParams({ period_start: start, period_end: end });
    return api.get<ContentMetric[]>(`${BASE}/releases/${releaseId}/content?${query}`);
  },
  learning: (releaseId: string, start: string, end: string) => {
    const query = new URLSearchParams({ period_start: start, period_end: end });
    return api.get<LearningMetric[]>(`${BASE}/releases/${releaseId}/learning?${query}`);
  },
  accessibility: (start: string, end: string, releaseId?: string) => {
    const query = new URLSearchParams({ period_start: start, period_end: end });
    if (releaseId) query.set("release_id", releaseId);
    return api.get<AccessibilityMetric>(`${BASE}/accessibility?${query}`);
  },
  exportCsv: (releaseId: string, start: string, end: string) => {
    const query = new URLSearchParams({ period_start: start, period_end: end });
    return apiBlob(`${BASE}/releases/${releaseId}/export.csv?${query}`);
  },
};
