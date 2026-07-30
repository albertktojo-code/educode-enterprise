import { ComicPresentationJoinPage } from "./ComicPresentationJoinPage";
import { ComicPresentationPage } from "./ComicPresentationPage";
import { ComicReaderLibraryPage } from "./ComicReaderLibraryPage";
import { ComicReaderPage } from "./ComicReaderPage";

export const comicReaderAccessRoutes = [
  { path: "/comic-reader", element: <ComicReaderLibraryPage /> },
  { path: "/comic-reader/releases/:releaseId", element: <ComicReaderPage /> },
  { path: "/comic-reader/join", element: <ComicPresentationJoinPage /> },
  { path: "/comic-reader/join/:joinCode", element: <ComicPresentationJoinPage /> },
  {
    path: "/teacher/comic-reader/presentations/:presentationId",
    element: <ComicPresentationPage />,
  },
];
