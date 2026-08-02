import type { RouteObject } from "react-router-dom";

import { AnimeStudioPage } from "./AnimeStudioPage";
import { AnimeStudentLibraryPage } from "./AnimeStudentLibraryPage";

export const animeStudioRoutes: RouteObject[] = [
  { path: "/anime-studio", element: <AnimeStudioPage /> },
  { path: "/anime-library", element: <AnimeStudentLibraryPage /> },
];
