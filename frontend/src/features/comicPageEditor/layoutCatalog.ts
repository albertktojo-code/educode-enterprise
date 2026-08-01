import type { LayoutTemplate, PanelRect } from "./types";

function layout(
  id: string,
  code: string,
  name: string,
  description: string,
  category: string,
  panels: PanelRect[],
): LayoutTemplate {
  return {
    id,
    code,
    name,
    description,
    version: "2.0.0",
    panelCount: panels.length,
    orientation: "PORTRAIT",
    category,
    gridDefinition: {
      gutter: 0.02,
      pageMargin: 0.02,
      panels,
    },
  };
}

export const fallbackLayouts: LayoutTemplate[] = [
  layout(
    "grid-feature-three",
    "GRID_FEATURE_THREE",
    "Destaque e três cenas",
    "Um quadro principal e três cenas de apoio.",
    "TRADITIONAL",
    [
      { x: 0, y: 0, width: 0.66, height: 0.5, shape: "RECTANGLE" },
      { x: 0.68, y: 0, width: 0.32, height: 0.5, shape: "RECTANGLE" },
      { x: 0, y: 0.52, width: 0.32, height: 0.48, shape: "RECTANGLE" },
      { x: 0.34, y: 0.52, width: 0.66, height: 0.48, shape: "RECTANGLE" },
    ],
  ),
  layout(
    "grid-equal-four",
    "GRID_EQUAL_FOUR",
    "Quatro quadros iguais",
    "Quatro cenas com o mesmo peso visual.",
    "TRADITIONAL",
    [
      { x: 0, y: 0, width: 0.49, height: 0.49, shape: "RECTANGLE" },
      { x: 0.51, y: 0, width: 0.49, height: 0.49, shape: "RECTANGLE" },
      { x: 0, y: 0.51, width: 0.49, height: 0.49, shape: "RECTANGLE" },
      { x: 0.51, y: 0.51, width: 0.49, height: 0.49, shape: "RECTANGLE" },
    ],
  ),
  layout(
    "grid-opening-scene",
    "GRID_OPENING_SCENE",
    "Cena de abertura",
    "Uma grande abertura e três quadros de progressão.",
    "CINEMATIC",
    [
      { x: 0, y: 0, width: 1, height: 0.58, shape: "RECTANGLE" },
      { x: 0, y: 0.6, width: 0.32, height: 0.4, shape: "RECTANGLE" },
      { x: 0.34, y: 0.6, width: 0.32, height: 0.4, shape: "RECTANGLE" },
      { x: 0.68, y: 0.6, width: 0.32, height: 0.4, shape: "RECTANGLE" },
    ],
  ),
  layout(
    "grid-dynamic-columns",
    "GRID_DYNAMIC_COLUMNS",
    "Duas colunas dinâmicas",
    "Colunas variadas para ação, explicação e reação.",
    "DYNAMIC",
    [
      { x: 0, y: 0, width: 0.56, height: 1, shape: "RECTANGLE" },
      { x: 0.58, y: 0, width: 0.42, height: 0.24, shape: "RECTANGLE" },
      { x: 0.58, y: 0.26, width: 0.42, height: 0.24, shape: "RECTANGLE" },
      { x: 0.58, y: 0.52, width: 0.42, height: 0.22, shape: "RECTANGLE" },
      { x: 0.58, y: 0.76, width: 0.42, height: 0.24, shape: "RECTANGLE" },
    ],
  ),
  layout(
    "grid-cinematic-strips",
    "GRID_CINEMATIC_STRIPS",
    "Faixa cinematográfica",
    "Três quadros horizontais para cenas panorâmicas.",
    "CINEMATIC",
    [
      { x: 0, y: 0, width: 1, height: 0.32, shape: "RECTANGLE" },
      { x: 0, y: 0.34, width: 1, height: 0.32, shape: "RECTANGLE" },
      { x: 0, y: 0.68, width: 1, height: 0.32, shape: "RECTANGLE" },
    ],
  ),
  layout(
    "grid-narrative-mosaic",
    "GRID_NARRATIVE_MOSAIC",
    "Mosaico narrativo",
    "Seis quadros variados para histórias densas.",
    "MOSAIC",
    [
      { x: 0, y: 0, width: 0.48, height: 0.36, shape: "RECTANGLE" },
      { x: 0.5, y: 0, width: 0.5, height: 0.24, shape: "RECTANGLE" },
      { x: 0.5, y: 0.26, width: 0.24, height: 0.34, shape: "RECTANGLE" },
      { x: 0.76, y: 0.26, width: 0.24, height: 0.34, shape: "RECTANGLE" },
      { x: 0, y: 0.38, width: 0.48, height: 0.62, shape: "RECTANGLE" },
      { x: 0.5, y: 0.62, width: 0.5, height: 0.38, shape: "RECTANGLE" },
    ],
  ),
  layout(
    "grid-action-page",
    "GRID_ACTION_PAGE",
    "Página de ação",
    "Contraste de tamanhos para clímax e resolução.",
    "ACTION",
    [
      { x: 0, y: 0, width: 0.62, height: 0.46, shape: "RECTANGLE" },
      { x: 0.64, y: 0, width: 0.36, height: 0.3, shape: "RECTANGLE" },
      { x: 0.64, y: 0.32, width: 0.36, height: 0.34, shape: "RECTANGLE" },
      { x: 0, y: 0.48, width: 0.36, height: 0.52, shape: "RECTANGLE" },
      { x: 0.38, y: 0.68, width: 0.62, height: 0.32, shape: "RECTANGLE" },
    ],
  ),
];

export function mergeLayouts(
  remote: LayoutTemplate[],
): LayoutTemplate[] {
  const byCode = new Map<string, LayoutTemplate>();
  [...fallbackLayouts, ...remote].forEach((item) => {
    byCode.set(item.code, item);
  });
  return [...byCode.values()];
}

export function layoutForPage(
  layouts: LayoutTemplate[],
  pageNumber: number,
  totalPages: number,
): LayoutTemplate {
  const ratio = totalPages <= 1 ? 0 : (pageNumber - 1) / (totalPages - 1);
  const code =
    pageNumber === 1
      ? "GRID_OPENING_SCENE"
      : ratio > 0.82
        ? "GRID_CINEMATIC_STRIPS"
        : ratio > 0.64
          ? "GRID_ACTION_PAGE"
          : ratio > 0.42
            ? "GRID_NARRATIVE_MOSAIC"
            : ratio > 0.2
              ? "GRID_DYNAMIC_COLUMNS"
              : "GRID_FEATURE_THREE";
  return (
    layouts.find((item) => item.code === code) ??
    layouts[pageNumber % layouts.length] ??
    fallbackLayouts[0]
  );
}
