import { api } from "../../lib/api";
import type {
  PresentationState,
  ReaderBookmark,
  ReaderManifest,
  ReaderPreferences,
  ReaderRelease,
  ReadingCheckpoint,
} from "./types";

const BASE = "/comic-reader";

export const comicReaderApi = {
  releases: () => api.get<ReaderRelease[]>(`${BASE}/releases`),
  manifest: (releaseId: string) =>
    api.get<ReaderManifest>(`${BASE}/releases/${releaseId}/manifest`),
  preferences: () => api.get<ReaderPreferences>(`${BASE}/preferences/me`),
  savePreferences: (data: ReaderPreferences) =>
    api.put<ReaderPreferences>(`${BASE}/preferences/me`, data),
  checkpoint: (releaseId: string) =>
    api.get<ReadingCheckpoint>(`${BASE}/releases/${releaseId}/checkpoint`),
  saveCheckpoint: (
    releaseId: string,
    data: {
      page_number: number;
      panel_number: number;
      completed_panels: number;
      elapsed_seconds: number;
      sequence: number;
      reader_mode: string;
      state: Record<string, unknown>;
    },
  ) => api.put(`${BASE}/releases/${releaseId}/checkpoint`, data),
  bookmarks: (releaseId: string) =>
    api.get<ReaderBookmark[]>(`${BASE}/releases/${releaseId}/bookmarks`),
  addBookmark: (
    releaseId: string,
    data: {
      page_number: number;
      panel_number?: number;
      label: string;
      note: string;
    },
  ) => api.post<{ id: string }>(`${BASE}/releases/${releaseId}/bookmarks`, data),
  deleteBookmark: (bookmarkId: string) =>
    api.delete<void>(`${BASE}/bookmarks/${bookmarkId}`),
  createPresentation: (releaseId: string, title: string) =>
    api.post<PresentationState>(`${BASE}/presentations`, {
      release_id: releaseId,
      title,
      allow_audience_join: true,
      sync_audience: true,
      reveal_mode: "PANEL",
      settings: {},
    }),
  presentation: (presentationId: string) =>
    api.get<PresentationState>(`${BASE}/presentations/${presentationId}`),
  presentationByCode: (code: string) =>
    api.get<PresentationState>(`${BASE}/presentations/code/${code}`),
  transitionPresentation: (
    presentationId: string,
    targetStatus: string,
    revision: number,
  ) =>
    api.post<PresentationState>(
      `${BASE}/presentations/${presentationId}/transition`,
      { target_status: targetStatus, expected_revision: revision },
    ),
  advancePresentation: (
    presentationId: string,
    data: {
      page_number: number;
      panel_number: number;
      reveal_step: number;
      presenter_note: string;
      expected_revision: number;
    },
  ) =>
    api.put<PresentationState>(
      `${BASE}/presentations/${presentationId}/position`,
      data,
    ),
  joinPresentation: (
    code: string,
    preferences: Partial<ReaderPreferences>,
  ) =>
    api.post<PresentationState>(`${BASE}/presentations/join/${code}`, {
      local_preferences: preferences,
    }),
  leavePresentation: (presentationId: string) =>
    api.post<{ left: boolean }>(`${BASE}/presentations/${presentationId}/leave`),
};
