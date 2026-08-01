import type { CSSProperties } from "react";

import type { ComicPage } from "./types";

interface Props {
  page?: ComicPage;
  selectedPanelId?: string;
  zoom: number;
  onSelectPanel: (panelId: string) => void;
}

const BASE_WIDTH = 620;
const BASE_HEIGHT = 827;

export function PagePreviewCanvas({
  page,
  selectedPanelId,
  zoom,
  onSelectPanel,
}: Props) {
  if (!page) {
    return (
      <div className="hq-empty-state">
        Selecione uma página para visualizar o rascunho estrutural.
      </div>
    );
  }

  const factor = zoom / 100;
  const wrapperStyle: CSSProperties = {
    width: BASE_WIDTH * factor,
    height: BASE_HEIGHT * factor,
  };
  const paperStyle: CSSProperties = {
    width: BASE_WIDTH,
    height: BASE_HEIGHT,
    transform: `scale(${factor})`,
    transformOrigin: "top left",
  };

  return (
    <div className="hq-page-stage">
      <div className="hq-page-zoom-wrapper" style={wrapperStyle}>
        <div
          className="hq-page-paper"
          style={paperStyle}
          role="group"
          aria-label={`Prévia da página ${page.pageNumber}`}
        >
          {page.panels.map((panel) => (
            <button
              type="button"
              key={panel.id}
              className={`hq-page-panel shape-${panel.shape.toLowerCase()} ${
                selectedPanelId === panel.id ? "is-selected" : ""
              }`}
              style={{
                left: `${panel.x * 100}%`,
                top: `${panel.y * 100}%`,
                width: `${panel.width * 100}%`,
                height: `${panel.height * 100}%`,
              }}
              onClick={() => onSelectPanel(panel.id)}
            >
              <span className="hq-panel-number">
                {panel.panelOrder}
              </span>
              <span className="hq-panel-placeholder">
                <strong>
                  {panel.sceneSummary || "Cena ainda não definida"}
                </strong>
                <small>
                  {panel.aspectRatio} · {panel.generationStatus}
                </small>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
