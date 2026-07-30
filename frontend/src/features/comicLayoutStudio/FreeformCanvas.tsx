import { useRef } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import type { CanvasDocument, CanvasGuide, CanvasLayer } from "./types";

interface Props {
  document: CanvasDocument;
  layers: CanvasLayer[];
  guides: CanvasGuide[];
  selectedLayerId?: string;
  zoom: number;
  onSelect: (id: string) => void;
  onMoveLayer: (id: string, x: number, y: number) => void;
}

export function FreeformCanvas({ document, layers, guides, selectedLayerId, zoom, onSelect, onMoveLayer }: Props) {
  const stageRef = useRef<HTMLDivElement | null>(null);

  function beginDrag(event: ReactPointerEvent<HTMLButtonElement>, layer: CanvasLayer) {
    if (layer.locked) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    const stage = stageRef.current?.getBoundingClientRect();
    if (!stage) return;
    const startX = event.clientX;
    const startY = event.clientY;
    const originX = layer.x;
    const originY = layer.y;
    const target = event.currentTarget;
    const move = (nativeEvent: PointerEvent) => {
      const dx = ((nativeEvent.clientX - startX) / stage.width) * document.pageWidth;
      const dy = ((nativeEvent.clientY - startY) / stage.height) * document.pageHeight;
      const grid = document.snapEnabled ? document.gridSize : 0.01;
      const x = Math.round((originX + dx) / grid) * grid;
      const y = Math.round((originY + dy) / grid) * grid;
      onMoveLayer(layer.id, x, y);
    };
    const end = () => {
      target.removeEventListener("pointermove", move);
      target.removeEventListener("pointerup", end);
    };
    target.addEventListener("pointermove", move);
    target.addEventListener("pointerup", end);
  }

  const scale = zoom / 100;
  return (
    <section className="cls-stage" aria-label="Canvas de diagramacao livre">
      <div className="cls-page-wrap" style={{ transform: `scale(${scale})` }}>
        {document.rulersEnabled && <><div className="cls-ruler cls-ruler-x" /><div className="cls-ruler cls-ruler-y" /></>}
        <div ref={stageRef} className="cls-page" style={{ aspectRatio: `${document.pageWidth}/${document.pageHeight}` }}>
          {document.showBleed && <div className="cls-bleed" aria-hidden="true" />}
          {document.showSafeArea && <div className="cls-safe" style={{ inset: `${(document.safeMarginMm / document.pageWidth) * 100}%` }} aria-hidden="true" />}
          {guides.filter((guide) => guide.visible).map((guide) => (
            <div key={guide.id} className={`cls-guide is-${guide.orientation.toLowerCase()}`} style={guide.orientation === "VERTICAL" ? { left: `${(guide.position / document.pageWidth) * 100}%` } : { top: `${(guide.position / document.pageHeight) * 100}%` }} />
          ))}
          {[...layers].sort((a, b) => a.zIndex - b.zIndex).filter((layer) => layer.visible).map((layer) => (
            <button
              type="button"
              key={layer.id}
              className={`cls-canvas-layer layer-${layer.layerType.toLowerCase()} shape-${layer.shape.toLowerCase()} ${selectedLayerId === layer.id ? "is-selected" : ""}`}
              style={{
                left: `${(layer.x / document.pageWidth) * 100}%`,
                top: `${(layer.y / document.pageHeight) * 100}%`,
                width: `${(layer.width / document.pageWidth) * 100}%`,
                height: `${(layer.height / document.pageHeight) * 100}%`,
                transform: `rotate(${layer.rotationDeg}deg)`,
                opacity: layer.opacity,
                zIndex: layer.zIndex,
              }}
              onPointerDown={(event) => beginDrag(event, layer)}
              onClick={() => onSelect(layer.id)}
              aria-label={`${layer.name}${layer.locked ? ", bloqueada" : ""}`}
            >
              <span className="cls-layer-content">{String(layer.content.text ?? layer.name)}</span>
              {layer.locked && <span className="cls-layer-lock" aria-hidden="true">🔒</span>}
              {selectedLayerId === layer.id && <><span className="cls-handle h-nw" /><span className="cls-handle h-ne" /><span className="cls-handle h-sw" /><span className="cls-handle h-se" /></>}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
