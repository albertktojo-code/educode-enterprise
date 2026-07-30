import type { CanvasLayer } from "./types";

interface Props {
  layers: CanvasLayer[];
  selectedLayerId?: string;
  onSelect: (id: string) => void;
  onToggleVisible: (id: string) => void;
  onToggleLocked: (id: string) => void;
  onMove: (id: string, direction: -1 | 1) => void;
  onAdd: (type: CanvasLayer["layerType"]) => void;
}

export function LayerPanel({ layers, selectedLayerId, onSelect, onToggleVisible, onToggleLocked, onMove, onAdd }: Props) {
  return (
    <aside className="cls-panel cls-layer-panel">
      <header><div><span className="cls-eyebrow">Estrutura</span><h2>Camadas</h2></div><button type="button" onClick={() => onAdd("SHAPE")}>+ Forma</button></header>
      <div className="cls-quick-add">
        <button type="button" onClick={() => onAdd("SPEECH_BALLOON")}>Balão</button>
        <button type="button" onClick={() => onAdd("CAPTION")}>Legenda</button>
        <button type="button" onClick={() => onAdd("DECORATION")}>Decoração</button>
      </div>
      <ol className="cls-layer-list">
        {[...layers].sort((a, b) => b.zIndex - a.zIndex).map((layer) => (
          <li key={layer.id} className={selectedLayerId === layer.id ? "is-selected" : ""}>
            <button type="button" className="cls-layer-main" onClick={() => onSelect(layer.id)}>
              <span className={`cls-layer-icon type-${layer.layerType.toLowerCase()}`} aria-hidden="true" />
              <span><strong>{layer.name}</strong><small>{layer.layerType} · nível {layer.zIndex}</small></span>
            </button>
            <div className="cls-layer-actions">
              <button type="button" aria-label={layer.visible ? "Ocultar camada" : "Mostrar camada"} onClick={() => onToggleVisible(layer.id)}>{layer.visible ? "◉" : "○"}</button>
              <button type="button" aria-label={layer.locked ? "Desbloquear camada" : "Bloquear camada"} onClick={() => onToggleLocked(layer.id)}>{layer.locked ? "🔒" : "🔓"}</button>
              <button type="button" aria-label="Subir camada" onClick={() => onMove(layer.id, 1)}>↑</button>
              <button type="button" aria-label="Descer camada" onClick={() => onMove(layer.id, -1)}>↓</button>
            </div>
          </li>
        ))}
      </ol>
    </aside>
  );
}
