import { AssessmentDeliveryPage } from "./AssessmentDeliveryPage";
import { StudentAssessmentsPage } from "./StudentAssessmentsPage";

export const assessmentDeliveryRoutes = [
  { path: "/teacher/assessment-delivery", element: <AssessmentDeliveryPage /> },
  { path: "/admin/assessment-delivery", element: <AssessmentDeliveryPage /> },
  { path: "/student/assessments", element: <StudentAssessmentsPage /> },
];
