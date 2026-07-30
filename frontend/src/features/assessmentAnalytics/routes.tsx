import type { ReactNode } from "react";
import { AssessmentAnalyticsDashboard } from "./AssessmentAnalyticsDashboard";
import { ItemAnalyticsPage } from "./ItemAnalyticsPage";
import { ReportAnalyticsPage } from "./ReportAnalyticsPage";
import { SkillAnalyticsPage } from "./SkillAnalyticsPage";

export interface AssessmentAnalyticsRoute { path: string; element: ReactNode; }

export const assessmentAnalyticsRoutes: AssessmentAnalyticsRoute[] = [
  { path: "/teacher/assessment-analytics", element: <AssessmentAnalyticsDashboard /> },
  { path: "/teacher/assessment-analytics/items", element: <ItemAnalyticsPage /> },
  { path: "/teacher/assessment-analytics/skills", element: <SkillAnalyticsPage /> },
  { path: "/admin/assessment-analytics/reports", element: <ReportAnalyticsPage /> },
];
