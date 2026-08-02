import { layoutForPage } from "./layoutCatalog";
import type { ComicPage, LayoutTemplate } from "./types";

export function makeStoryPage(
  pageNumber: number,
  totalPages: number,
  layouts: LayoutTemplate[],
): ComicPage {
  const layout = layoutForPage(layouts, pageNumber, totalPages);
  return {
    id: `draft-story-page-${pageNumber}`,
    pageNumber,
    pageType: "STORY",
    status: "DRAFT",
    pageWidth: 1200,
    pageHeight: 1600,
    layoutTemplateId: layout.id,
    backgroundSettings: {},
    accessibilitySettings: {},
    contentLayers: [],
    preservationSettings: {},
    continuityMetadata: {},
    coverGeneration: {},
    revisionNumber: 1,
    panels: layout.gridDefinition.panels.map((panel, index) => ({
      ...panel,
      id: `draft-story-page-${pageNumber}-panel-${index + 1}`,
      panelOrder: index + 1,
      aspectRatio: panel.width > panel.height ? "4:3" : "3:4",
      sceneSummary: `Página ${pageNumber}, cena ${index + 1}`,
      visualPrompt: "",
      generationStatus: "PENDING",
      lockedElements: [],
    })),
  };
}

export function synchronizeStoryPages(
  pages: ComicPage[],
  totalStoryPages: number,
  layouts: LayoutTemplate[],
): ComicPage[] {
  const normalizedTotal = Math.max(1, Math.trunc(totalStoryPages));
  const existingStoryPages = pages.filter(
    (page) => page.pageType === "STORY",
  );
  const storyPages = Array.from(
    { length: normalizedTotal },
    (_, index) => {
      const pageNumber = index + 1;
      const existing = existingStoryPages[index];
      return existing
        ? { ...existing, pageNumber }
        : makeStoryPage(pageNumber, normalizedTotal, layouts);
    },
  );
  const covers = pages.filter((page) => page.pageType === "COVER");
  const backCovers = pages.filter(
    (page) => page.pageType === "BACK_COVER",
  );
  const supplementaryPages = pages.filter(
    (page) => !["COVER", "STORY", "BACK_COVER"].includes(page.pageType),
  );
  return [
    ...covers,
    ...storyPages,
    ...supplementaryPages,
    ...backCovers,
  ];
}

export function applyLayoutToStoryPage(
  page: ComicPage,
  layout: LayoutTemplate,
): ComicPage {
  const panels = layout.gridDefinition.panels.map((panel, index) => ({
    ...panel,
    id: page.panels[index]?.id ?? `${page.id}-panel-${index + 1}`,
    panelOrder: index + 1,
    aspectRatio: panel.width > panel.height ? "4:3" : "3:4",
    sceneSummary: page.panels[index]?.sceneSummary ?? "Nova cena",
    visualPrompt: page.panels[index]?.visualPrompt ?? "",
    generationStatus:
      page.panels[index]?.generationStatus ?? "PENDING",
    lockedElements: page.panels[index]?.lockedElements ?? [],
  }));
  return {
    ...page,
    layoutTemplateId: layout.id,
    panels,
  };
}

export function varyStoryPageLayouts(
  pages: ComicPage[],
  layouts: LayoutTemplate[],
  random: () => number = Math.random,
): ComicPage[] {
  if (!layouts.length) return pages;
  let previousLayoutId: string | null = null;
  return pages.map((page) => {
    if (page.pageType !== "STORY") return page;
    const candidates = layouts.filter(
      (layout) => layout.id !== previousLayoutId,
    );
    const pool = candidates.length ? candidates : layouts;
    const index = Math.min(
      pool.length - 1,
      Math.floor(random() * pool.length),
    );
    const layout = pool[Math.max(0, index)];
    previousLayoutId = layout.id;
    return applyLayoutToStoryPage(page, layout);
  });
}
