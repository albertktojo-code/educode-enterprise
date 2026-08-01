import type { ReactNode } from "react";

import { adaptiveEvolutionRoutes } from "../adaptiveEvolution/routes";
import { adaptiveInsightsRoutes } from "../adaptiveInsights/routes";
import { animeStudioRoutes } from "../animeStudio/routes";
import { assessmentAnalyticsRoutes } from "../assessmentAnalytics/routes";
import { assessmentDeliveryRoutes } from "../assessmentDelivery/routes";
import { assessmentHubRoutes } from "../assessmentHub/routes";
import { assessmentReviewRoutes } from "../assessmentReview/routes";
import { comicLayoutStudioRoutes } from "../comicLayoutStudio/routes";
import { comicPageEditorRoutes } from "../comicPageEditor/routes";
import { comicReviewPublishRoutes } from "../comicReviewPublish/routes";
import { comicReaderAccessRoutes } from "../comicReaderAccess/routes";
import { comicReaderAnalyticsRoutes } from "../comicReaderAnalytics/routes";
import { comicVisualLibraryRoutes } from "../comicVisualLibrary/routes";
import { instrumentGovernanceRoutes } from "../instrumentGovernance/routes";
import { interventionOrchestrationRoutes } from "../interventionOrchestration/routes";
import { interventionEffectivenessRoutes } from "../interventionEffectiveness/routes";
import { institutionalGovernanceRoutes } from "../institutionalGovernance/routes";
import { hqStudentExperienceRoutes } from "../hqStudentExperience/routes";

export interface ConsolidatedFeatureRoute {
  path: string;
  element: ReactNode;
}

function normalize(
  routes: Array<{ path?: string; element?: ReactNode }>,
): ConsolidatedFeatureRoute[] {
  return routes
    .filter(
      (route): route is { path: string; element: ReactNode } =>
        Boolean(route.path && route.element),
    )
    .map((route) => ({
      path: route.path.replace(/^\/+/, ""),
      element: route.element,
    }));
}

export const consolidatedFeatureRoutes: ConsolidatedFeatureRoute[] = [
  ...normalize(adaptiveEvolutionRoutes),
  ...normalize(adaptiveInsightsRoutes),
  ...normalize(animeStudioRoutes),
  ...normalize(assessmentAnalyticsRoutes),
  ...normalize(assessmentDeliveryRoutes),
  ...normalize(assessmentHubRoutes),
  ...normalize(assessmentReviewRoutes),
  ...normalize(comicPageEditorRoutes),
  ...normalize(comicLayoutStudioRoutes),
  ...normalize(comicVisualLibraryRoutes),
  ...normalize(comicReviewPublishRoutes),
  ...normalize(comicReaderAccessRoutes),
  ...normalize(comicReaderAnalyticsRoutes),
  ...normalize(instrumentGovernanceRoutes),
  ...normalize(interventionOrchestrationRoutes),
  ...normalize(interventionEffectivenessRoutes),
  ...normalize(institutionalGovernanceRoutes),
  ...normalize(hqStudentExperienceRoutes),
];
