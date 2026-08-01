import { ReviewWorkspace } from "./ReviewWorkspace";

export const comicReviewPublishRoutes = [
  {
    path: "/teacher/my-comics/:projectId/review",
    element: <ReviewWorkspace />,
  },
  {
    path: "/teacher/comic-studio/:projectId/review",
    element: <ReviewWorkspace />,
  },
  {
    path: "/admin/comic-publications",
    element: <ReviewWorkspace />,
  },
];
