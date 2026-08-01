import type {
  ChangeEvent,
} from "react";

import type {
  ComicPanel,
  PreservationOption,
  StoryPlan,
} from "./types";

interface Props {
  panel?: ComicPanel;
  panelCount: number;
  storyPlan: StoryPlan;
  preservationOptions: PreservationOption[];
  busy: boolean;
  onChangeStoryPlan: (patch: Partial<StoryPlan>) => void;
  onChangePanel: (patch: Partial<ComicPanel>) => void;
  onSaveStory: () => void;
  onGenerateStory: () => void;
  onDistributeStory: () => void;
  onSavePanel: () => void;
  onRegenerate: () => void;
  onLock: (key: string) => void;
}

const icons: Record<string, string> = {
  character: "●",
  outfit: "◆",
  scenario: "▲",
  framing: "▣",
  expression: "☺",
  palette: "◉",
  style: "✦",
};

export function PanelInspector({
  panel,
  panelCount,
  storyPlan,
  preservationOptions,
  busy,
  onChangeStoryPlan,
  onChangePanel,
  onSaveStory,
  onGenerateStory,
  onDistributeStory,
  onSavePanel,
  onRegenerate,
  onLock,
}: Props) {
  return (
    <aside className="hq-inspector">
      <div className="hq-inspector-title-row">
        <div>
          <span className="hq-eyebrow">Quadro selecionado</span>
          <h2>
            {panel ? `Quadro ${panel.panelOrder}` : "Nenhum quadro"}
          </h2>
        </div>
        <span className="hq-frame-count">
          {panel ? `${panel.panelOrder} de ${panelCount}` : "—"}
        </span>
      </div>

      <div className="hq-script-tabs" role="tablist">
        <button
          type="button"
          className={
            storyPlan.sourceMode === "MANUAL" ? "is-active" : ""
          }
          onClick={() =>
            onChangeStoryPlan({ sourceMode: "MANUAL" })
          }
        >
          ▤ Roteiro manual
        </button>
        <button
          type="button"
          className={
            storyPlan.sourceMode === "AI_SUMMARY"
              ? "is-active"
              : ""
          }
          onClick={() =>
            onChangeStoryPlan({ sourceMode: "AI_SUMMARY" })
          }
        >
          ✦ Gerar com IA
        </button>
      </div>

      {storyPlan.sourceMode === "MANUAL" ? (
        <label className="hq-script-field">
          <span>Roteiro completo da HQ</span>
          <textarea
            className="hq-large-textarea"
            value={storyPlan.fullScript}
            maxLength={100000}
            placeholder={
              "Escreva a história completa, incluindo páginas, cenas, " +
              "diálogos, narrações e orientações visuais."
            }
            onChange={(
              event: ChangeEvent<HTMLTextAreaElement>,
            ) =>
              onChangeStoryPlan({
                fullScript: event.target.value,
              })
            }
          />
          <small>
            {storyPlan.fullScript.length.toLocaleString("pt-BR")} caracteres
          </small>
        </label>
      ) : (
        <label className="hq-script-field">
          <span>Resumo curto da história</span>
          <textarea
            className="hq-large-textarea"
            value={storyPlan.shortSummary}
            maxLength={6000}
            placeholder={
              "Informe tema, objetivo pedagógico, personagens e o desafio. " +
              "A IA transformará o resumo em roteiro multipágina."
            }
            onChange={(
              event: ChangeEvent<HTMLTextAreaElement>,
            ) =>
              onChangeStoryPlan({
                shortSummary: event.target.value,
              })
            }
          />
          <small>
            {storyPlan.shortSummary.length.toLocaleString("pt-BR")} / 6.000
          </small>
        </label>
      )}

      <div className="hq-story-actions">
        <button
          type="button"
          className="hq-secondary-color"
          disabled={busy}
          onClick={onSaveStory}
        >
          Salvar roteiro
        </button>
        {storyPlan.sourceMode === "AI_SUMMARY" ? (
          <button
            type="button"
            className="hq-ai-button"
            disabled={busy}
            onClick={onGenerateStory}
          >
            ✦ Gerar roteiro com IA
          </button>
        ) : null}
        <button
          type="button"
          className="hq-success-button"
          disabled={busy}
          onClick={onDistributeStory}
        >
          Distribuir nas páginas
        </button>
      </div>

      <div className="hq-inspector-divider" />

      {!panel ? (
        <p>Selecione um quadro na página para editar a cena.</p>
      ) : (
        <>
          <label>
            <span>Resumo da cena</span>
            <textarea
              value={panel.sceneSummary}
              maxLength={2000}
              placeholder="Resuma o que acontece neste quadro..."
              onChange={(
                event: ChangeEvent<HTMLTextAreaElement>,
              ) =>
                onChangePanel({
                  sceneSummary: event.target.value,
                })
              }
            />
            <small>{panel.sceneSummary.length} / 2.000</small>
          </label>

          <label>
            <span>Prompt visual</span>
            <textarea
              value={panel.visualPrompt}
              maxLength={5000}
              placeholder={
                "Descreva composição, ângulo, cores, iluminação, " +
                "expressões e clima da cena."
              }
              onChange={(
                event: ChangeEvent<HTMLTextAreaElement>,
              ) =>
                onChangePanel({
                  visualPrompt: event.target.value,
                })
              }
            />
            <small>{panel.visualPrompt.length} / 5.000</small>
          </label>

          <div className="hq-locks">
            <div className="hq-lock-heading">
              <strong>Preservar ao regenerar</strong>
              <span title="Os itens selecionados não serão alterados.">
                ⓘ
              </span>
            </div>
            <div className="hq-lock-chip-grid">
              {preservationOptions.map((option) => {
                const selected = panel.lockedElements.includes(
                  option.key,
                );
                return (
                  <button
                    type="button"
                    key={option.key}
                    className={`hq-lock-chip lock-${option.key} ${
                      selected ? "is-locked" : ""
                    }`}
                    aria-pressed={selected}
                    onClick={() => onLock(option.key)}
                  >
                    <span>{icons[option.key] ?? "●"}</span>
                    {option.label}
                    {selected ? <b>✓</b> : null}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="hq-panel-actions">
            <button
              type="button"
              className="hq-secondary-color"
              disabled={busy}
              onClick={onSavePanel}
            >
              Salvar quadro
            </button>
            <button
              type="button"
              className="hq-regenerate-button"
              disabled={busy}
              onClick={onRegenerate}
            >
              ✦ Regenerar quadro
            </button>
          </div>
        </>
      )}
    </aside>
  );
}
