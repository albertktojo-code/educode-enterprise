import type { ExportPreset } from "./types";

interface Props { open: boolean; presets: ExportPreset[]; selectedId?: string; onSelect: (id: string) => void; onClose: () => void; onExport: () => void; }

export function ExportDialog({ open, presets, selectedId, onSelect, onClose, onExport }: Props) {
  if (!open) return null;
  return (
    <div className="cls-modal-backdrop" role="presentation">
      <section className="cls-modal" role="dialog" aria-modal="true" aria-labelledby="export-title">
        <header><div><span className="cls-eyebrow">Saída profissional</span><h2 id="export-title">Exportar HQ</h2></div><button type="button" onClick={onClose} aria-label="Fechar">×</button></header>
        <div className="cls-preset-grid">{presets.map((preset) => <button type="button" key={preset.id} className={selectedId === preset.id ? "is-selected" : ""} onClick={() => onSelect(preset.id)}><strong>{preset.name}</strong><span>{preset.outputFormat} · {preset.pageSize} · {preset.dpi} DPI</span><small>{preset.includeBleed ? "Com sangria" : "Sem sangria"}{preset.includeCropMarks ? " · marcas de corte" : ""}</small></button>)}</div>
        <footer><button type="button" onClick={onClose}>Cancelar</button><button type="button" className="cls-primary" onClick={onExport} disabled={!selectedId}>Executar pré-flight e exportar</button></footer>
      </section>
    </div>
  );
}
