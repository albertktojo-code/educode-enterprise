import type { RouteObject } from "react-router-dom";

import { AnimeStudioPage } from "./AnimeStudioPage";

export const animeStudioRoutes: RouteObject[] =
  [{ path: "/anime-studio", element: <AnimeStudioPage /> }];
