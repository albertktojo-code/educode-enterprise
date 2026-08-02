import type { LayoutTemplate } from "./types";

interface Props {
  layouts: LayoutTemplate[];
  selectedId?: string;
  onSelect: (layout: LayoutTemplate) => void;
  onAutoArrange: () => void;
  autoArrangeDisabled?: boolean;
}

export function LayoutLibraryPanel({
  layouts,
  selectedId,
  onSelect,
  onAutoArrange,
  autoArrangeDisabled = false,
}: Props) {
  return (
    <aside
      className="hq-layout-library"
      aria-label="Biblioteca de grids"
    >
      <div className="hq-panel-heading">
        <div>
          <span className="hq-eyebrow">Estrutura da página</span>
          <h2>Escolha um grid</h2>
        </div>
        <button
          type="button"
          className="hq-icon-button"
          aria-label="Filtrar grids"
        >
          ◉ Filtros
        </button>
      </div>

      <p className="hq-panel-helper">
        Cada página pode usar um grid diferente. A narrativa será
        redistribuída conforme a quantidade real de quadros.
      </p>

      <button
        type="button"
        className="hq-primary hq-auto-grid-button"
        onClick={onAutoArrange}
        disabled={autoArrangeDisabled}
      >
        ✦ IA variar grids por página
      </button>

      <div className="hq-layout-list">
        {layouts.map((layout) => (
          <button
            key={layout.id}
            type="button"
            className={`hq-layout-card ${
              selectedId === layout.id ? "is-selected" : ""
            }`}
            onClick={() => onSelect(layout)}
          >
            <span
              className="hq-layout-miniature"
              aria-hidden="true"
            >
              {layout.gridDefinition.panels.map((panel, index) => (
                <span
                  key={index}
                  className="hq-mini-panel"
                  style={{
                    left: `${panel.x * 100}%`,
                    top: `${panel.y * 100}%`,
                    width: `${panel.width * 100}%`,
                    height: `${panel.height * 100}%`,
                  }}
                />
              ))}
            </span>
            <span className="hq-layout-card-copy">
              <strong>{layout.name}</strong>
              <small>
                {layout.panelCount} quadros ·{" "}
                {layout.category.toLowerCase()}
              </small>
              <em>{layout.description}</em>
            </span>
            {selectedId === layout.id ? (
              <span className="hq-layout-check">✓</span>
            ) : null}
          </button>
        ))}
      </div>

    </aside>
  );
}
