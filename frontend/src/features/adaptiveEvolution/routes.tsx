import type { RouteObject } from "react-router-dom";
import { AccessibilityStudioPage } from "./pages/AccessibilityStudioPage";
import { AdaptiveEvolutionDashboard } from "./pages/AdaptiveEvolutionDashboard";
import { DifficultyAnalysisPage } from "./pages/DifficultyAnalysisPage";
import { FeedbackLabPage } from "./pages/FeedbackLabPage";
import { HintStudioPage } from "./pages/HintStudioPage";
import { ProgressionRulesPage } from "./pages/ProgressionRulesPage";
import { ReviewSimulatorPage } from "./pages/ReviewSimulatorPage";

export const adaptiveEvolutionRoutes: RouteObject[] = [
  { path: "/teacher/adaptive-evolution", element: <AdaptiveEvolutionDashboard /> },
  { path: "/teacher/adaptive-evolution/hints", element: <HintStudioPage /> },
  { path: "/teacher/adaptive-evolution/reviews", element: <ReviewSimulatorPage /> },
  { path: "/teacher/adaptive-evolution/feedback", element: <FeedbackLabPage /> },
  { path: "/teacher/adaptive-evolution/difficulty", element: <DifficultyAnalysisPage /> },
  { path: "/teacher/adaptive-evolution/progression", element: <ProgressionRulesPage /> },
  { path: "/teacher/adaptive-evolution/accessibility", element: <AccessibilityStudioPage /> },
];
