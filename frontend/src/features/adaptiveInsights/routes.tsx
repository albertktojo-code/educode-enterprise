import type { RouteObject } from "react-router-dom";
import { AdaptiveInsightsDashboard } from "./pages/AdaptiveInsightsDashboard";
import { AdaptiveModelsPage } from "./pages/AdaptiveModelsPage";
import { ControlledExperimentsPage } from "./pages/ControlledExperimentsPage";
import { InstitutionalPathsPage } from "./pages/InstitutionalPathsPage";
import { InterventionHistoryPage } from "./pages/InterventionHistoryPage";
import { MaterialEffectivenessPage } from "./pages/MaterialEffectivenessPage";
import { RecommendationSimulationPage } from "./pages/RecommendationSimulationPage";

export const adaptiveInsightsRoutes: RouteObject[] = [
  { path: "/teacher/adaptive-insights", element: <AdaptiveInsightsDashboard /> },
  { path: "/teacher/adaptive-insights/interventions", element: <InterventionHistoryPage /> },
  { path: "/teacher/adaptive-insights/materials", element: <MaterialEffectivenessPage /> },
  { path: "/teacher/adaptive-insights/paths", element: <InstitutionalPathsPage /> },
  { path: "/teacher/adaptive-insights/models", element: <AdaptiveModelsPage /> },
  { path: "/teacher/adaptive-insights/simulation", element: <RecommendationSimulationPage /> },
  { path: "/teacher/adaptive-insights/experiments", element: <ControlledExperimentsPage /> },
];
