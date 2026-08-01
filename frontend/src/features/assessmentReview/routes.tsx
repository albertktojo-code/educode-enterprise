import type { ReactNode } from "react";

import { AppealManagementPage } from "./AppealManagementPage";
import { AssessmentReviewPage } from "./AssessmentReviewPage";
import { RubricManagementPage } from "./RubricManagementPage";

export interface AssessmentReviewRoute {
  path: string;
  element: ReactNode;
}

export const assessmentReviewRoutes: AssessmentReviewRoute[] = [
  { path: "/teacher/assessment-review", element: <AssessmentReviewPage /> },
  { path: "/admin/assessment-rubrics", element: <RubricManagementPage /> },
  { path: "/teacher/assessment-appeals", element: <AppealManagementPage /> },
];
