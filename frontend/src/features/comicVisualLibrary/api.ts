import { api } from "../../lib/api";
import type { ComicCharacter, ComicScenario, ConsistencyFinding, GenerationBatch, VisualLibrary } from "./types";

const BASE = "/comic-visual-library";

export const comicVisualLibraryApi = {
  listLibraries: () => api.get<VisualLibrary[]>(`${BASE}/libraries`),
  listCharacters: (libraryId?: string) =>
    api.get<ComicCharacter[]>(`${BASE}/characters${libraryId ? `?library_id=${libraryId}` : ""}`),
  createCharacter: (payload: unknown) => api.post<ComicCharacter>(`${BASE}/characters`, payload),
  listScenarios: (libraryId?: string) =>
    api.get<ComicScenario[]>(`${BASE}/scenarios${libraryId ? `?library_id=${libraryId}` : ""}`),
  listConsistency: (projectId: string) =>
    api.get<ConsistencyFinding[]>(`${BASE}/projects/${projectId}/consistency`),
  resolveFinding: (findingId: string, payload: unknown) =>
    api.post(`${BASE}/consistency/${findingId}/resolve`, payload),
  getBatch: (batchId: string) => api.get<GenerationBatch>(`${BASE}/generation-batches/${batchId}`),
};
