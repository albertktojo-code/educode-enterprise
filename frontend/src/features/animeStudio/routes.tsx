import type { RouteObject } from "react-router-dom";

import { AnimeStudioPage } from "./AnimeStudioPage";
import { AnimeStudentLibraryPage } from "./AnimeStudentLibraryPage";
import { AnimeAnalyticsPage } from "./AnimeAnalyticsPage";

export const animeStudioRoutes: RouteObject[] = [
  { path: "/anime-studio", element: <AnimeStudioPage /> },
  { path: "/anime-library", element: <AnimeStudentLibraryPage /> },
  { path: "/analytics/anime/:projectId", element: <AnimeAnalyticsPage /> },
];
