import type { RouteObject } from "react-router-dom";
import { ComicPageEditor } from "./ComicPageEditor";
import { ComicStudioEntryPage } from "./ComicStudioEntryPage";
import { GenerationLoadingPage } from "./GenerationLoadingPage";

export const comicPageEditorRoutes: RouteObject[] = [
  { path: "/teacher/comic-studio", element: <ComicStudioEntryPage /> },
  { path: "/teacher/comic-studio/editor/:projectId", element: <ComicPageEditor /> },
  { path: "/teacher/comic-studio/generation/:jobId", element: <GenerationLoadingPage /> },
  { path: "/teacher/my-comics/:projectId/pages", element: <ComicPageEditor /> },
];
