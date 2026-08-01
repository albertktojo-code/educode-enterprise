import { useMemo, useState } from "react";
import { ExportDialog } from "./ExportDialog";
import { FreeformCanvas } from "./FreeformCanvas";
import { GuideToolbar } from "./GuideToolbar";
import { LayerPanel } from "./LayerPanel";
import { PreflightPanel } from "./PreflightPanel";
import { PropertiesPanel } from "./PropertiesPanel";
import type { CanvasDocument, CanvasGuide, CanvasLayer, ExportPreset, PreflightFinding } from "./types";
import "./styles.css";

const initialDocument: CanvasDocument = {
  id: "document-demo", comicProjectId: "project-demo", pageId: "page-demo", name: "Página 1 — layout livre",
  pageWidth: 210, pageHeight: 297, dpi: 300, bleedMm: 3, safeMarginMm: 8, gridSize: 5,
  snapEnabled: true, rulersEnabled: true, showBleed: true, showSafeArea: true, revisionNumber: 1,
};

const initialLayers: CanvasLayer[] = [
  { id: "layer-image", layerType: "IMAGE", name: "Cena principal", zIndex: 1, x: 8, y: 10, width: 132, height: 128, rotationDeg: -2, opacity: 1, visible: true, locked: false, shape: "ANGLED", style: {}, content: { text: "Imagem principal", source_dpi: 300 }, accessibilityMetadata: { alt_text: "Personagens resolvendo um desafio" } },
  { id: "layer-panel", layerType: "PANEL", name: "Quadro lateral", zIndex: 2, x: 144, y: 16, width: 58, height: 108, rotationDeg: 2, opacity: 1, visible: true, locked: false, shape: "ROUNDED", style: {}, content: { text: "Cena 2" }, accessibilityMetadata: {} },
  { id: "layer-balloon", layerType: "SPEECH_BALLOON", name: "Fala da Luna", zIndex: 3, x: 92, y: 28, width: 70, height: 38, rotationDeg: 0, opacity: 1, visible: true, locked: false, shape: "ELLIPSE", style: { font_size: 14 }, content: { text: "Vamos decompor o problema!" }, accessibilityMetadata: {} },
  { id: "layer-caption", layerType: "CAPTION", name: "Narração", zIndex: 4, x: 18, y: 154, width: 174, height: 30, rotationDeg: 0, opacity: 1, visible: true, locked: false, shape: "RECTANGLE", style: { font_size: 13 }, content: { text: "Cada pista revela uma parte da solução." }, accessibilityMetadata: {} },
];

const presets: ExportPreset[] = [
  { id: "pdf", code: "PDF_PRINT_A4", name: "PDF A4 para impressão", outputFormat: "PDF", pageSize: "A4", dpi: 300, includeBleed: true, includeCropMarks: true },
  { id: "png", code: "PNG_CLASSROOM", name: "PNG para apresentação", outputFormat: "PNG", pageSize: "CUSTOM", dpi: 144, includeBleed: false, includeCropMarks: false },
  { id: "web", code: "WEB_READING", name: "Leitura digital acessível", outputFormat: "WEBP", pageSize: "RESPONSIVE", dpi: 144, includeBleed: false, includeCropMarks: false },
];

export function ComicLayoutStudio() {
  const [document, setDocument] = useState(initialDocument);
  const [layers, setLayers] = useState(initialLayers);
  const [guides, setGuides] = useState<CanvasGuide[]>([{ id: "guide-center", orientation: "VERTICAL", position: 105, guideType: "CENTER", visible: true, locked: true, label: "Centro" }]);
  const [selectedLayerId, setSelectedLayerId] = useState<string | undefined>(initialLayers[2].id);
  const [zoom, setZoom] = useState(82);
  const [findings, setFindings] = useState<PreflightFinding[]>([]);
  const [exportOpen, setExportOpen] = useState(false);
  const [presetId, setPresetId] = useState<string | undefined>(undefined);
  const selectedLayer = useMemo(() => layers.find((item) => item.id === selectedLayerId), [layers, selectedLayerId]);

  function patchLayer(id: string, patch: Partial<CanvasLayer>) {
    setLayers((current) => current.map((item) => item.id === id ? { ...item, ...patch } : item));
  }
  function moveLayer(id: string, direction: -1 | 1) {
    const ordered = [...layers].sort((a, b) => a.zIndex - b.zIndex);
    const index = ordered.findIndex((item) => item.id === id);
    const target = Math.max(0, Math.min(ordered.length - 1, index + direction));
    [ordered[index], ordered[target]] = [ordered[target], ordered[index]];
    setLayers(ordered.map((item, zIndex) => ({ ...item, zIndex: zIndex + 1 })));
  }
  function addLayer(layerType: CanvasLayer["layerType"]) {
    const id = `layer-${Date.now()}`;
    const layer: CanvasLayer = { id, layerType, name: `Nova camada ${layers.length + 1}`, zIndex: layers.length + 1, x: 55, y: 90, width: 80, height: 45, rotationDeg: 0, opacity: 1, visible: true, locked: false, shape: layerType.includes("BALLOON") ? "ELLIPSE" : "ROUNDED", style: { font_size: 14 }, content: { text: layerType === "SHAPE" ? "" : "Edite este conteúdo" }, accessibilityMetadata: {} };
    setLayers([...layers, layer]); setSelectedLayerId(id);
  }
  function runPreflight() {
    const next: PreflightFinding[] = [];
    layers.forEach((layer) => {
      if (layer.layerType === "IMAGE" && !layer.accessibilityMetadata.alt_text) next.push({ severity: "WARNING", code: "IMAGE_ALT_TEXT_MISSING", message: `${layer.name}: adicione descrição alternativa.` });
      if (["SPEECH_BALLOON", "CAPTION", "NARRATION"].includes(layer.layerType) && Number(layer.style.font_size ?? 14) < 10) next.push({ severity: "WARNING", code: "FONT_TOO_SMALL", message: `${layer.name}: fonte abaixo de 10 pt.` });
      if (layer.x < 0 || layer.y < 0 || layer.x + layer.width > document.pageWidth || layer.y + layer.height > document.pageHeight) next.push({ severity: "INFO", code: "LAYER_CROSSES_TRIM", message: `${layer.name} ultrapassa a área de corte.` });
    });
    setFindings(next);
  }

  return (
    <main className="cls-shell">
      <header className="cls-header"><div><span className="cls-eyebrow">EduCode Comic Studio</span><h1>Layout livre e diagramação avançada</h1><p>Organize quadros, balões e elementos em camadas com controle editorial.</p></div><div className="cls-header-actions"><span className="cls-save">Salvo agora · revisão {document.revisionNumber}</span><button type="button" onClick={() => setExportOpen(true)}>Prévia e exportação</button><button type="button" className="cls-primary" onClick={() => setExportOpen(true)}>Exportar HQ</button></div></header>
      <GuideToolbar {...document} zoom={zoom} onZoom={setZoom} onToggle={(key) => setDocument((current) => ({ ...current, [key]: !current[key] }))} onAddGuide={(orientation) => setGuides([...guides, { id: `guide-${Date.now()}`, orientation, position: orientation === "VERTICAL" ? document.pageWidth / 3 : document.pageHeight / 3, guideType: "CUSTOM", visible: true, locked: false }])} />
      <div className="cls-workspace">
        <LayerPanel layers={layers} selectedLayerId={selectedLayerId} onSelect={setSelectedLayerId} onToggleVisible={(id) => { const item = layers.find((layer) => layer.id === id); if (item) patchLayer(id, { visible: !item.visible }); }} onToggleLocked={(id) => { const item = layers.find((layer) => layer.id === id); if (item) patchLayer(id, { locked: !item.locked }); }} onMove={moveLayer} onAdd={addLayer} />
        <div className="cls-center"><div className="cls-page-meta"><strong>{document.name}</strong><span>{document.pageWidth} × {document.pageHeight} mm · {document.dpi} DPI · sangria {document.bleedMm} mm</span><div><button type="button">Desfazer</button><button type="button">Refazer</button></div></div><FreeformCanvas document={document} layers={layers} guides={guides} selectedLayerId={selectedLayerId} zoom={zoom} onSelect={setSelectedLayerId} onMoveLayer={(id, x, y) => patchLayer(id, { x, y })} /><PreflightPanel findings={findings} onRun={runPreflight} /></div>
        <PropertiesPanel layer={selectedLayer} onChange={(patch) => selectedLayer && patchLayer(selectedLayer.id, patch)} onDelete={() => { if (!selectedLayer) return; setLayers(layers.filter((item) => item.id !== selectedLayer.id)); setSelectedLayerId(undefined); }} />
      </div>
      <ExportDialog open={exportOpen} presets={presets} selectedId={presetId} onSelect={setPresetId} onClose={() => setExportOpen(false)} onExport={() => { runPreflight(); setExportOpen(false); alert("Exportação adicionada à fila com pré-flight obrigatório."); }} />
    </main>
  );
}
