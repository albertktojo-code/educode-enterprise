import type { ReaderMode, ReaderOrientation, ReaderPreferences } from "./types";

export function AccessibilityToolbar({
  preferences,
  onChange,
  onNarrate,
  onStopNarration,
}: {
  preferences: ReaderPreferences;
  onChange: (preferences: ReaderPreferences) => void;
  onNarrate: () => void;
  onStopNarration: () => void;
}) {
  const set = <K extends keyof ReaderPreferences>(
    key: K,
    value: ReaderPreferences[K],
  ) => onChange({ ...preferences, [key]: value });

  return (
    <section className="reader-toolbar" aria-label="Preferências de leitura">
      <label>
        Modo
        <select
          value={preferences.reader_mode}
          onChange={(event) =>
            set("reader_mode", event.target.value as ReaderMode)
          }
        >
          <option value="PAGE">Página</option>
          <option value="PANEL">Quadro a quadro</option>
          <option value="VERTICAL">Rolagem vertical</option>
          <option value="FOCUS">Modo foco</option>
        </select>
      </label>

      <label>
        Tamanho do texto
        <input
          type="range"
          min="0.75"
          max="2.5"
          step="0.05"
          value={preferences.font_scale}
          onChange={(event) => set("font_scale", Number(event.target.value))}
        />
      </label>

      <label>
        Zoom da página · {Math.round(preferences.zoom_level * 100)}%
        <span className="reader-zoom-control">
          <button type="button" aria-label="Diminuir zoom" onClick={() => set("zoom_level", Math.max(0.5, Number((preferences.zoom_level - 0.1).toFixed(1))))}>−</button>
          <input
            aria-label="Nível de zoom"
            type="range"
            min="0.5"
            max="2.5"
            step="0.1"
            value={preferences.zoom_level}
            onChange={(event) => set("zoom_level", Number(event.target.value))}
          />
          <button type="button" aria-label="Aumentar zoom" onClick={() => set("zoom_level", Math.min(2.5, Number((preferences.zoom_level + 0.1).toFixed(1))))}>+</button>
        </span>
      </label>

      <label>
        Orientação
        <select
          value={preferences.orientation}
          onChange={(event) => set("orientation", event.target.value as ReaderOrientation)}
        >
          <option value="AUTO">Automática</option>
          <option value="PORTRAIT">Retrato</option>
          <option value="LANDSCAPE">Paisagem</option>
        </select>
      </label>

      <label>
        Espaçamento
        <input
          type="range"
          min="1"
          max="2.5"
          step="0.1"
          value={preferences.line_spacing}
          onChange={(event) => set("line_spacing", Number(event.target.value))}
        />
      </label>

      <label>
        Velocidade da narração
        <input
          type="range"
          min="0.5"
          max="2"
          step="0.1"
          value={preferences.narration_rate}
          onChange={(event) => set("narration_rate", Number(event.target.value))}
        />
      </label>

      <label className="reader-check">
        <input
          type="checkbox"
          checked={preferences.high_contrast}
          onChange={(event) => set("high_contrast", event.target.checked)}
        />
        Alto contraste
      </label>

      <label className="reader-check">
        <input
          type="checkbox"
          checked={preferences.reduced_motion}
          onChange={(event) => set("reduced_motion", event.target.checked)}
        />
        Reduzir movimento
      </label>

      <label className="reader-check">
        <input
          type="checkbox"
          checked={preferences.show_alt_text}
          onChange={(event) => set("show_alt_text", event.target.checked)}
        />
        Mostrar descrição alternativa
      </label>

      <label className="reader-check">
        <input
          type="checkbox"
          checked={preferences.screen_reader_mode}
          onChange={(event) => set("screen_reader_mode", event.target.checked)}
        />
        Modo leitor de tela
      </label>

      <label className="reader-check">
        <input
          type="checkbox"
          checked={preferences.auto_play_narration}
          onChange={(event) => set("auto_play_narration", event.target.checked)}
        />
        Narrar ao avançar
      </label>

      <div className="button-row">
        <button type="button" onClick={onNarrate}>Narrar</button>
        <button type="button" onClick={onStopNarration}>Parar</button>
      </div>
    </section>
  );
}
