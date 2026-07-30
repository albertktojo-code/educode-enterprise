interface Props {
  snapEnabled: boolean;
  rulersEnabled: boolean;
  showBleed: boolean;
  showSafeArea: boolean;
  zoom: number;
  onToggle: (key: "snapEnabled" | "rulersEnabled" | "showBleed" | "showSafeArea") => void;
  onZoom: (value: number) => void;
  onAddGuide: (orientation: "HORIZONTAL" | "VERTICAL") => void;
}

export function GuideToolbar({ snapEnabled, rulersEnabled, showBleed, showSafeArea, zoom, onToggle, onZoom, onAddGuide }: Props) {
  return (
    <div className="cls-toolbar" aria-label="Ferramentas de diagramacao">
      <button type="button" aria-pressed={snapEnabled} onClick={() => onToggle("snapEnabled")}>Imã {snapEnabled ? "ativo" : "inativo"}</button>
      <button type="button" aria-pressed={rulersEnabled} onClick={() => onToggle("rulersEnabled")}>Réguas</button>
      <button type="button" aria-pressed={showBleed} onClick={() => onToggle("showBleed")}>Sangria</button>
      <button type="button" aria-pressed={showSafeArea} onClick={() => onToggle("showSafeArea")}>Área segura</button>
      <button type="button" onClick={() => onAddGuide("VERTICAL")}>+ Guia vertical</button>
      <button type="button" onClick={() => onAddGuide("HORIZONTAL")}>+ Guia horizontal</button>
      <label>Zoom <input type="range" min="55" max="130" value={zoom} onChange={(event) => onZoom(Number(event.target.value))} /></label>
      <span>{zoom}%</span>
    </div>
  );
}
