import type { CanvasLayer } from "./types";

interface Props {
  layer?: CanvasLayer;
  onChange: (patch: Partial<CanvasLayer>) => void;
  onDelete: () => void;
}

function NumberField({ label, value, onChange, step = 1 }: { label: string; value: number; onChange: (value: number) => void; step?: number }) {
  return <label>{label}<input type="number" value={Number(value.toFixed(2))} step={step} onChange={(event) => onChange(Number(event.target.value))} /></label>;
}

export function PropertiesPanel({ layer, onChange, onDelete }: Props) {
  if (!layer) return <aside className="cls-panel cls-properties"><div className="cls-empty">Selecione uma camada para editar posição, tamanho e estilo.</div></aside>;
  return (
    <aside className="cls-panel cls-properties">
      <header><div><span className="cls-eyebrow">Inspetor</span><h2>{layer.name}</h2></div><button type="button" onClick={onDelete} disabled={layer.locked}>Excluir</button></header>
      <label>Nome<input value={layer.name} onChange={(event) => onChange({ name: event.target.value })} /></label>
      <div className="cls-field-grid">
        <NumberField label="X (mm)" value={layer.x} onChange={(x) => onChange({ x })} />
        <NumberField label="Y (mm)" value={layer.y} onChange={(y) => onChange({ y })} />
        <NumberField label="Largura" value={layer.width} onChange={(width) => onChange({ width })} />
        <NumberField label="Altura" value={layer.height} onChange={(height) => onChange({ height })} />
        <NumberField label="Rotação" value={layer.rotationDeg} step={1} onChange={(rotationDeg) => onChange({ rotationDeg })} />
        <NumberField label="Opacidade" value={layer.opacity} step={0.05} onChange={(opacity) => onChange({ opacity: Math.max(0, Math.min(1, opacity)) })} />
      </div>
      <label>Forma<select value={layer.shape} onChange={(event) => onChange({ shape: event.target.value })}><option>RECTANGLE</option><option>ROUNDED</option><option>CIRCLE</option><option>ELLIPSE</option><option>POLYGON</option><option>ANGLED</option></select></label>
      <label>Texto<textarea value={String(layer.content.text ?? "")} onChange={(event) => onChange({ content: { ...layer.content, text: event.target.value } })} /></label>
      <label>Descrição acessível<textarea value={String(layer.accessibilityMetadata.alt_text ?? "")} onChange={(event) => onChange({ accessibilityMetadata: { ...layer.accessibilityMetadata, alt_text: event.target.value } })} /></label>
      <div className="cls-lock-row"><label><input type="checkbox" checked={layer.locked} onChange={(event) => onChange({ locked: event.target.checked })} /> Bloquear</label><label><input type="checkbox" checked={layer.visible} onChange={(event) => onChange({ visible: event.target.checked })} /> Visível</label></div>
    </aside>
  );
}
