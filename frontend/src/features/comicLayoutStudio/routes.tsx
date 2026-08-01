import type { RouteObject } from "react-router-dom";
import { ComicLayoutStudio } from "./ComicLayoutStudio";

export const comicLayoutStudioRoutes: RouteObject[] = [
  { path: "/teacher/comic-studio/layout/:projectId/:pageId", element: <ComicLayoutStudio /> },
  { path: "/teacher/my-comics/:projectId/layout/:pageId", element: <ComicLayoutStudio /> },
];
