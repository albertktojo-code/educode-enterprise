export type ReviewStatus =
  | "DRAFT" | "OPEN" | "IN_REVIEW" | "CHANGES_REQUESTED"
  | "APPROVED" | "CLOSED" | "CANCELLED";

export type ThreadStatus = "OPEN" | "RESOLVED" | "REOPENED";
export type ReleaseStatus = "DRAFT" | "READY" | "SCHEDULED" | "PUBLISHED" | "WITHDRAWN" | "ARCHIVED";

export interface ReviewSession {
  id: string;
  comic_project_id: string;
  title: string;
  description: string;
  status: ReviewStatus;
  due_at?: string;
}

export interface ReviewThread {
  id: string;
  title: string;
  status: ThreadStatus;
  anchor_type: "PROJECT" | "PAGE" | "PANEL" | "LAYER";
  page_id?: string;
  panel_id?: string;
  layer_id?: string;
}

export interface EditorialChecklistItem {
  code: string;
  category: string;
  label: string;
  required: boolean;
  status: "PENDING" | "PASSED" | "FAILED" | "WAIVED";
}

export interface PublicationRelease {
  id: string;
  release_number: number;
  release_name: string;
  release_hash: string;
  status: ReleaseStatus;
}
