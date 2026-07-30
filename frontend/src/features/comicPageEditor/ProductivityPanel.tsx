import type {
  ComicPage,
  ProductivityAnalysis,
} from "./types";

interface Props {
  open: boolean;
  pages: ComicPage[];
  analysis: ProductivityAnalysis | null;
  busy: boolean;
  onClose: () => void;
  onAnalyze: () => void;
  onMovePage: (pageId: string, direction: -1 | 1) => void;
  onMovePanel: (
    pageId: string,
    panelId: string,
    direction: -1 | 1,
  ) => void;
  onSaveLayout: (pageId: string) => void;
}

export function ProductivityPanel({
  open,
  pages,
  analysis,
  busy,
  onClose,
  onAnalyze,
  onMovePage,
  onMovePanel,
  onSaveLayout,
}: Props) {
  if (!open) return null;
  const storyPages = pages.filter(
    (page) => page.pageType === "STORY",
  );

  return (
    <div
      className="productivity-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Produtividade avançada"
    >
      <section className="productivity-dialog">
        <header>
          <div>
            <span className="hq-eyebrow">
              Sprint 16.10.2
            </span>
            <h2>Produtividade e assistente narrativo</h2>
          </div>
          <button type="button" onClick={onClose}>
            Fechar
          </button>
        </header>

        <div className="productivity-summary">
          <article>
            <strong>
              {analysis?.publicationStatus ?? "NÃO ANALISADO"}
            </strong>
            <span>Estado para publicação</span>
          </article>
          <article>
            <strong>
              {analysis?.rhythm.averagePanelsPerPage ?? "—"}
            </strong>
            <span>Média de quadros por página</span>
          </article>
          <article>
            <strong>
              {analysis?.readability.blocked ?? "—"}
            </strong>
            <span>Quadros bloqueados</span>
          </article>
          <button
            type="button"
            className="hq-ai-button"
            disabled={busy}
            onClick={onAnalyze}
          >
            ✦ Analisar ritmo e legibilidade
          </button>
        </div>

        {analysis ? (
          <div className="productivity-warnings">
            {analysis.rhythm.warnings.map((warning) => (
              <article key={`${warning.code}-${warning.pageNumber ?? 0}`}>
                <b>{warning.severity}</b>
                <span>{warning.message}</span>
                {warning.pageNumber ? (
                  <small>Página {warning.pageNumber}</small>
                ) : null}
              </article>
            ))}
            {analysis.readability.panels
              .flatMap((panel) =>
                panel.warnings.map((warning) => ({
                  ...warning,
                  panelOrder: panel.panelOrder,
                })),
              )
              .map((warning, index) => (
                <article key={`${warning.code}-${index}`}>
                  <b>{warning.severity}</b>
                  <span>{warning.message}</span>
                  <small>Quadro {warning.panelOrder}</small>
                </article>
              ))}
          </div>
        ) : null}

        <div className="productivity-organizer">
          <h3>Organizar páginas e ordem de leitura</h3>
          {storyPages.map((page, pageIndex) => (
            <article key={page.id} className="productivity-page-card">
              <header>
                <strong>Página {page.pageNumber}</strong>
                <div>
                  <button
                    type="button"
                    disabled={pageIndex === 0}
                    onClick={() => onMovePage(page.id, -1)}
                    aria-label="Mover página para trás"
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    disabled={pageIndex === storyPages.length - 1}
                    onClick={() => onMovePage(page.id, 1)}
                    aria-label="Mover página para frente"
                  >
                    ↓
                  </button>
                  <button
                    type="button"
                    onClick={() => onSaveLayout(page.id)}
                  >
                    Salvar grid
                  </button>
                </div>
              </header>
              <div className="productivity-panel-order">
                {page.panels.map((panel, panelIndex) => (
                  <div key={panel.id}>
                    <span>Quadro {panel.panelOrder}</span>
                    <button
                      type="button"
                      disabled={panelIndex === 0}
                      onClick={() =>
                        onMovePanel(page.id, panel.id, -1)
                      }
                    >
                      ←
                    </button>
                    <button
                      type="button"
                      disabled={panelIndex === page.panels.length - 1}
                      onClick={() =>
                        onMovePanel(page.id, panel.id, 1)
                      }
                    >
                      →
                    </button>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
