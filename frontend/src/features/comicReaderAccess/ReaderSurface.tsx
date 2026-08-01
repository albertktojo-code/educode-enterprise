import type { ReaderMode, ReaderPage, ReaderPanel, ReaderPreferences } from "./types";

function panelImage(panel: ReaderPanel): string | null {
  return panel.image_asset_path ?? panel.image_url ?? null;
}

function PanelCard({
  panel,
  preferences,
}: {
  panel: ReaderPanel;
  preferences: ReaderPreferences;
}) {
  const image = panelImage(panel);
  return (
    <article className="reader-panel-card">
      {image ? (
        <img src={image} alt={panel.alt_text ?? ""} />
      ) : (
        <div className="reader-panel-placeholder">
          <strong>Quadro {panel.panel_number ?? ""}</strong>
          <p>{panel.scene_description ?? panel.narrative_goal ?? "Cena da HQ"}</p>
        </div>
      )}
      <div className="reader-dialogues">
        {(panel.balloons ?? []).map((balloon, index) => (
          <blockquote key={balloon.id ?? `${index}-${balloon.text ?? ""}`}>
            {balloon.speaker_name_snapshot ? (
              <strong>{balloon.speaker_name_snapshot}</strong>
            ) : null}
            <span>{balloon.text ?? ""}</span>
          </blockquote>
        ))}
      </div>
      {preferences.show_alt_text ? (
        <p className="reader-alt-text">
          {panel.alt_text || "Descrição alternativa ainda não cadastrada."}
        </p>
      ) : null}
    </article>
  );
}

function orderedPanels(page: ReaderPage): ReaderPanel[] {
  return [...(page.panels ?? [])].sort(
    (left, right) => (left.reading_order ?? 0) - (right.reading_order ?? 0),
  );
}

export function ReaderSurface({
  pages,
  pageIndex,
  panelIndex,
  mode,
  preferences,
}: {
  pages: ReaderPage[];
  pageIndex: number;
  panelIndex: number;
  mode: ReaderMode;
  preferences: ReaderPreferences;
}) {
  if (!pages.length) {
    return <div className="panel">O release não possui páginas no snapshot.</div>;
  }

  if (mode === "VERTICAL") {
    return (
      <div className="reader-vertical">
        {pages.map((page, index) => (
          <section className="reader-page-stack" key={page.id ?? index}>
            <h2>{page.title || `Página ${page.page_number ?? index + 1}`}</h2>
            {orderedPanels(page).map((panel, panelPosition) => (
              <PanelCard
                key={panel.id ?? panelPosition}
                panel={panel}
                preferences={preferences}
              />
            ))}
          </section>
        ))}
      </div>
    );
  }

  const page = pages[pageIndex] ?? pages[0];
  const panels = orderedPanels(page);

  if (mode === "PANEL" || mode === "FOCUS") {
    const panel = panels[panelIndex] ?? panels[0];
    return panel ? (
      <PanelCard panel={panel} preferences={preferences} />
    ) : (
      <div className="panel">A página não possui quadros.</div>
    );
  }

  return (
    <section className="reader-page-stack">
      <h2>{page.title || `Página ${page.page_number ?? pageIndex + 1}`}</h2>
      <div className="reader-page-grid">
        {panels.map((panel, index) => (
          <PanelCard
            key={panel.id ?? index}
            panel={panel}
            preferences={preferences}
          />
        ))}
      </div>
    </section>
  );
}
