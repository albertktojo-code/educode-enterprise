import type { RouteObject } from "react-router-dom";
import { ComicVisualLibrary } from "./ComicVisualLibrary";

export const comicVisualLibraryRoutes: RouteObject[] = [
  { path: "/teacher/comic-studio/visual-library/:projectId", element: <ComicVisualLibrary /> },
  { path: "/teacher/my-comics/:projectId/visual-library", element: <ComicVisualLibrary /> },
  { path: "/admin/comic-visual-library", element: <ComicVisualLibrary /> },
];
