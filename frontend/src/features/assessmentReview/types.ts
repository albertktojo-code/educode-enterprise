export type ReviewAssignmentStatus =
  | "PENDING"
  | "IN_REVIEW"
  | "COMPLETED"
  | "REOPENED"
  | "CANCELLED";

export interface ReviewAssignment {
  id: string;
  attempt_id: string;
  response_id: string;
  reviewer_user_id: string;
  status: ReviewAssignmentStatus;
  priority: number;
  due_at?: string | null;
  blinded: boolean;
}

export interface ReviewRubric {
  id: string;
  code: string;
  name: string;
  description: string;
  status: "DRAFT" | "PUBLISHED" | "DEPRECATED" | "ARCHIVED";
  current_version: number;
}

export interface ReviewAppeal {
  id: string;
  attempt_id: string;
  response_id?: string | null;
  student_id: string;
  reason_code: string;
  statement: string;
  status: string;
}
