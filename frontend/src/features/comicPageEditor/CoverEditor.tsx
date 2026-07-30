import type {
  ChangeEvent,
  CSSProperties,
} from "react";

import type {
  CoverComposition,
  CoverDraft,
  CoverTextLayer,
} from "./types";

interface Props {
  cover: CoverDraft;
  compositions: CoverComposition[];
  zoom: number;
  busy: boolean;
  onChange: (patch: Partial<CoverDraft>) => void;
  onChangeLayer: (
    layerId: string,
    patch: Partial<CoverTextLayer>,
  ) => void;
  onSave: () => void;
  onGenerate: () => void;
  onApplyReadyResult: () => void;
  onCreateBackCover: () => void;
}

function layerStyle(layer: CoverTextLayer): CSSProperties {
  const fontSize = Number(layer.style.font_size ?? 36);
  return {
    left: `${layer.x * 100}%`,
    top: `${layer.y * 100}%`,
    width: `${layer.width * 100}%`,
    height: `${layer.height * 100}%`,
    color: String(layer.style.color ?? "#ffffff"),
    fontSize,
    fontWeight: Number(layer.style.font_weight ?? 700),
    textAlign: String(
      layer.style.align ?? "center",
    ) as CSSProperties["textAlign"],
    textShadow: layer.style.shadow
      ? "0 3px 12px rgba(0,0,0,.7)"
      : undefined,
    WebkitTextStroke: layer.style.outline
      ? "1px rgba(0,0,0,.55)"
      : undefined,
  };
}

export function CoverEditor({
  cover,
  compositions,
  zoom,
  busy,
  onChange,
  onChangeLayer,
  onSave,
  onGenerate,
  onApplyReadyResult,
  onCreateBackCover,
}: Props) {
  const factor = zoom / 100;
  const image = cover.backgroundAssetReference;

  return (
    <section className="cover-editor">
      <aside className="cover-composition-panel">
        <span className="hq-eyebrow">Capa sem grids</span>
        <h2>Composição da capa</h2>
        <p>
          A capa ocupa a página inteira. Títulos e créditos
          continuam editáveis e não são incorporados pela IA.
        </p>
        <div className="cover-composition-list">
          {compositions.map((item) => (
            <button
              type="button"
              key={item.code}
              className={
                cover.compositionCode === item.code
                  ? "is-selected"
                  : ""
              }
              onClick={() =>
                onChange({ compositionCode: item.code })
              }
            >
              <span className={`cover-template template-${item.code.toLowerCase()}`}>
                <i />
                <b />
                <em />
              </span>
              <span>
                <strong>{item.label}</strong>
                <small>{item.description}</small>
              </span>
            </button>
          ))}
        </div>

        <div className="cover-guide-options">
          <label>
            <input
              type="checkbox"
              checked={cover.bleedEnabled}
              onChange={(event) =>
                onChange({ bleedEnabled: event.target.checked })
              }
            />
            Mostrar sangria
          </label>
          <label>
            <input
              type="checkbox"
              checked={cover.safeAreaEnabled}
              onChange={(event) =>
                onChange({
                  safeAreaEnabled: event.target.checked,
                })
              }
            />
            Mostrar área segura
          </label>
          <label>
            <input
              type="checkbox"
              checked={cover.spineEnabled}
              onChange={(event) =>
                onChange({ spineEnabled: event.target.checked })
              }
            />
            Reservar lombada
          </label>
        </div>
      </aside>

      <div className="cover-canvas-area">
        <div
          className="cover-zoom-wrapper"
          style={{
            width: 600 * factor,
            height: 800 * factor,
          }}
        >
          <div
            className="cover-paper"
            style={{
              width: 600,
              height: 800,
              transform: `scale(${factor})`,
              transformOrigin: "top left",
              backgroundImage: image
                ? `linear-gradient(rgba(15,23,42,.12), rgba(15,23,42,.26)), url("${image}")`
                : "linear-gradient(145deg, #4b38cf, #7c49e5 46%, #2478ef)",
              backgroundPosition: `${cover.focalPoint.x * 100}% ${cover.focalPoint.y * 100}%`,
              backgroundSize: `${cover.scale * 100}%`,
            }}
          >
            {cover.bleedEnabled ? (
              <span className="cover-bleed-guide" />
            ) : null}
            {cover.safeAreaEnabled ? (
              <span className="cover-safe-guide" />
            ) : null}
            {cover.spineEnabled ? (
              <span className="cover-spine-guide" />
            ) : null}

            <div className="cover-art-placeholder">
              {image ? null : (
                <>
                  <strong>Arte principal da capa</strong>
                  <small>
                    Gere com IA ou informe uma imagem de fundo.
                  </small>
                </>
              )}
            </div>

            {cover.contentLayers
              .filter((layer) => layer.visible)
              .map((layer) => (
                <div
                  className={`cover-text-layer layer-${layer.layerType.toLowerCase()}`}
                  key={layer.id}
                  style={layerStyle(layer)}
                >
                  {layer.content ||
                    (layer.layerType === "TITLE"
                      ? "Título da HQ"
                      : layer.layerType === "SUBTITLE"
                        ? "Subtítulo"
                        : "Créditos")}
                </div>
              ))}
          </div>
        </div>
      </div>

      <aside className="cover-inspector">
        <span className="hq-eyebrow">Conteúdo editável</span>
        <h2>Informações da capa</h2>

        <label>
          Título
          <input
            value={cover.title}
            onChange={(event: ChangeEvent<HTMLInputElement>) => {
              const value = event.target.value;
              onChange({ title: value });
              const titleLayer = cover.contentLayers.find(
                (layer) => layer.layerType === "TITLE",
              );
              if (titleLayer) {
                onChangeLayer(titleLayer.id, { content: value });
              }
            }}
          />
        </label>
        <label>
          Subtítulo
          <input
            value={cover.subtitle}
            onChange={(event) => {
              const value = event.target.value;
              onChange({ subtitle: value });
              const layer = cover.contentLayers.find(
                (item) => item.layerType === "SUBTITLE",
              );
              if (layer) onChangeLayer(layer.id, { content: value });
            }}
          />
        </label>
        <div className="cover-field-grid">
          <label>
            Disciplina
            <input
              value={cover.discipline}
              onChange={(event) =>
                onChange({ discipline: event.target.value })
              }
            />
          </label>
          <label>
            Tema
            <input
              value={cover.theme}
              onChange={(event) =>
                onChange({ theme: event.target.value })
              }
            />
          </label>
          <label>
            Autor/professor
            <input
              value={cover.author}
              onChange={(event) =>
                onChange({ author: event.target.value })
              }
            />
          </label>
          <label>
            Escola
            <input
              value={cover.school}
              onChange={(event) =>
                onChange({ school: event.target.value })
              }
            />
          </label>
          <label>
            Turma
            <input
              value={cover.classroom}
              onChange={(event) =>
                onChange({ classroom: event.target.value })
              }
            />
          </label>
          <label>
            Ano escolar
            <input
              value={cover.schoolYear}
              onChange={(event) =>
                onChange({ schoolYear: event.target.value })
              }
            />
          </label>
        </div>

        <label>
          Imagem de fundo ou referência
          <input
            value={cover.backgroundAssetReference ?? ""}
            placeholder="URL ou referência do ativo institucional"
            onChange={(event) =>
              onChange({
                backgroundAssetReference:
                  event.target.value || null,
              })
            }
          />
        </label>

        <label>
          Escala da imagem: {cover.scale.toFixed(2)}×
          <input
            type="range"
            min={0.5}
            max={3}
            step={0.05}
            value={cover.scale}
            onChange={(event) =>
              onChange({ scale: Number(event.target.value) })
            }
          />
        </label>

        <div className="cover-preservation">
          <strong>Preservar na capa</strong>
          {[
            "Personagem",
            "Roupa",
            "Cenário",
            "Paleta",
            "Estilo visual",
          ].map((label) => (
            <span key={label}>✓ {label}</span>
          ))}
        </div>

        <div className="cover-action-stack">
          <button
            type="button"
            className="hq-secondary-color"
            disabled={busy}
            onClick={onSave}
          >
            Salvar capa
          </button>
          <button
            type="button"
            className="hq-ai-button"
            disabled={busy}
            onClick={onGenerate}
          >
            ✦ Gerar quatro variações
          </button>
          <button
            type="button"
            className="hq-compare-button"
            disabled={busy}
            onClick={onApplyReadyResult}
          >
            ◫ Comparar variação pronta
          </button>
          <button
            type="button"
            className="hq-success-button"
            disabled={busy}
            onClick={onCreateBackCover}
          >
            Criar contracapa
          </button>
        </div>

        <p className="cover-ai-rule">
          A IA recebe a regra obrigatória: não inserir letras,
          títulos, palavras ou logotipos na imagem.
        </p>
      </aside>
    </section>
  );
}
