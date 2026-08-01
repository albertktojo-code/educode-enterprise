import type { ComicPage } from "./types";

interface Props {
  pages: ComicPage[];
  selectedPageId?: string;
  onSelect: (pageId: string) => void;
  onPrevious: () => void;
  onNext: () => void;
}

export function PageThumbnailStrip({
  pages,
  selectedPageId,
  onSelect,
  onPrevious,
  onNext,
}: Props) {
  const selectedIndex = Math.max(
    0,
    pages.findIndex((page) => page.id === selectedPageId),
  );
  return (
    <nav className="hq-page-strip" aria-label="Páginas da HQ">
      <div className="hq-page-navigation">
        <button
          type="button"
          onClick={onPrevious}
          disabled={selectedIndex <= 0}
          aria-label="Página anterior"
        >
          ‹
        </button>
        <span>
          Página <strong>{selectedIndex + 1}</strong> de{" "}
          <strong>{Math.max(1, pages.length)}</strong>
        </span>
        <button
          type="button"
          onClick={onNext}
          disabled={selectedIndex >= pages.length - 1}
          aria-label="Próxima página"
        >
          ›
        </button>
      </div>

      <div className="hq-page-thumbnails">
        {pages.map((page) => (
          <button
            type="button"
            key={page.id}
            className={`hq-page-thumb ${
              selectedPageId === page.id ? "is-selected" : ""
            }`}
            onClick={() => onSelect(page.id)}
          >
            <span
              className={`hq-thumb-paper page-type-${page.pageType.toLowerCase()}`}
            >
              {page.pageType === "STORY"
                ? page.panels.map((panel) => (
                    <span
                      key={panel.id}
                      style={{
                        left: `${panel.x * 100}%`,
                        top: `${panel.y * 100}%`,
                        width: `${panel.width * 100}%`,
                        height: `${panel.height * 100}%`,
                      }}
                    />
                  ))
                : (
                    <b className="hq-special-page-symbol">
                      {page.pageType === "COVER"
                        ? "CAPA"
                        : page.pageType === "BACK_COVER"
                          ? "VERSO"
                          : page.pageType === "ACTIVITY"
                            ? "ATV"
                            : "GAB"}
                    </b>
                  )}
            </span>
            <small>
              {page.pageType === "COVER"
                ? "Capa"
                : page.pageType === "BACK_COVER"
                  ? "Contracapa"
                  : page.pageType === "STORY"
                    ? `Página ${page.pageNumber}`
                    : page.title ?? `Página ${page.pageNumber}`}
            </small>
          </button>
        ))}
      </div>
    </nav>
  );
}
