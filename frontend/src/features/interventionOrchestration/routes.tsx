import { InterventionOrchestrationPage } from "./InterventionOrchestrationPage";
import { StudentInterventionsPage } from "./StudentInterventionsPage";

export const interventionOrchestrationRoutes = [
  {
    path: "/teacher/interventions",
    element: <InterventionOrchestrationPage />,
  },
  {
    path: "/student/interventions",
    element: <StudentInterventionsPage />,
  },
];
