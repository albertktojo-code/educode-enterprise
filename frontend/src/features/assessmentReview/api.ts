import { api } from "../../lib/api";
import type { ReviewAppeal, ReviewAssignment, ReviewRubric } from "./types";

const BASE = "/assessment-review";

export const assessmentReviewApi = {
  listAssignments: () => api.get<ReviewAssignment[]>(`${BASE}/assignments`),
  listRubrics: () => api.get<ReviewRubric[]>(`${BASE}/rubrics`),
  listAppeals: () => api.get<ReviewAppeal[]>(`${BASE}/appeals`),
  startAssignment: (id: string) =>
    api.post<ReviewAssignment>(`${BASE}/assignments/${id}/start`),
};
