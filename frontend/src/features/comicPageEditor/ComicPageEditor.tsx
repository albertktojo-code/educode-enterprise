import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
} from "react";
import { useNavigate, useParams } from "react-router-dom";

import { comicPageEditorApi } from "./api";
import { ActivityStudio } from "./ActivityStudio";
import { ComparisonDialog } from "./ComparisonDialog";
import { ContinuityPanel } from "./ContinuityPanel";
import { DeliveryStudio } from "./DeliveryStudio";
import { EditorialPanel } from "./EditorialPanel";
import { FeedbackStudio } from "./FeedbackStudio";
import { CoverEditor } from "./CoverEditor";
import {
  createHistory,
  pushHistory,
  redoHistory,
  sha256,
  undoHistory,
} from "./editorState";
import {
  fallbackLayouts,
  mergeLayouts,
} from "./layoutCatalog";
import { LayoutLibraryPanel } from "./LayoutLibraryPanel";
import { PagePreviewCanvas } from "./PagePreviewCanvas";
import { PageThumbnailStrip } from "./PageThumbnailStrip";
import {
  applyLayoutToStoryPage,
  makeStoryPage,
  synchronizeStoryPages,
  varyStoryPageLayouts,
} from "./pageCollection";
import { PanelInspector } from "./PanelInspector";
import { ProductivityPanel } from "./ProductivityPanel";
import type {
  ComicPage,
  ComicPanel,
  ContinuityIssue,
  ContinuityRow,
  CoverComposition,
  CoverDraft,
  DistributionMode,
  EditorSnapshot,
  LayoutTemplate,
  NarrativePacing,
  PreservationOption,
  ProductivityAnalysis,
  StoryPlan,
} from "./types";
import "./styles.css";

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const defaultPreservationOptions: PreservationOption[] = [
  { key: "character", label: "Personagem" },
  { key: "outfit", label: "Roupa" },
  { key: "scenario", label: "Cenário" },
  { key: "framing", label: "Enquadramento" },
  { key: "expression", label: "Expressão" },
  { key: "palette", label: "Paleta" },
  { key: "style", label: "Estilo visual" },
];

function defaultStoryPlan(projectId: string): StoryPlan {
  return {
    exists: false,
    comicProjectId: projectId,
    sourceMode: "MANUAL",
    totalPages: 8,
    narrativePacing: "BALANCED",
    distributionMode: "AUTOMATIC",
    shortSummary: "",
    fullScript: "",
    pagePlan: [],
    continuityConstraints: {},
    generationInstructions: {
      vary_layouts: true,
      respect_page_capacity: true,
      teacher_review_required: true,
    },
    generationStatus: "DRAFT",
    aiGenerationRequestId: null,
    revisionNumber: 0,
  };
}

function defaultCover(): CoverDraft {
  return {
    compositionCode: "CINEMATIC",
    title: "Título da HQ",
    subtitle: "",
    author: "",
    school: "",
    classroom: "",
    discipline: "",
    theme: "",
    schoolYear: "",
    backgroundAssetReference: null,
    focalPoint: { x: 0.5, y: 0.5 },
    scale: 1,
    bleedEnabled: true,
    safeAreaEnabled: true,
    spineEnabled: false,
    contentLayers: [
      {
        id: "cover-title",
        layerType: "TITLE",
        content: "Título da HQ",
        x: 0.08,
        y: 0.07,
        width: 0.84,
        height: 0.18,
        visible: true,
        style: {
          fontSize: 54,
          color: "#ffffff",
          align: "center",
          shadow: true,
        },
      },
    ],
    preservationSettings: {
      scope: "PROJECT",
      elements: [
        "character",
        "outfit",
        "scenario",
        "palette",
        "style",
      ],
    },
    continuityMetadata: {},
    accessibilitySettings: {},
    coverGeneration: {},
    revisionNumber: 0,
  };
}

function coverAsPage(cover: CoverDraft): ComicPage {
  return {
    id: cover.id ?? "demo-cover",
    pageNumber: 0,
    pageType: "COVER",
    title: cover.title,
    status: "DRAFT",
    pageWidth: 1200,
    pageHeight: 1600,
    layoutTemplateId: null,
    backgroundSettings: {
      compositionCode: cover.compositionCode,
      subtitle: cover.subtitle,
      author: cover.author,
      discipline: cover.discipline,
      theme: cover.theme,
      backgroundAssetReference: cover.backgroundAssetReference,
      focalPoint: cover.focalPoint,
      scale: cover.scale,
    },
    accessibilitySettings: cover.accessibilitySettings,
    contentLayers: cover.contentLayers,
    preservationSettings: cover.preservationSettings,
    continuityMetadata: cover.continuityMetadata,
    coverGeneration: cover.coverGeneration,
    revisionNumber: cover.revisionNumber,
    panels: [],
  };
}

function snapshotOf(
  pages: ComicPage[],
  storyPlan: StoryPlan,
  cover: CoverDraft | null,
  selectedPageId: string,
  selectedPanelId: string,
  zoom: number,
): EditorSnapshot {
  return structuredClone({
    pages,
    storyPlan,
    cover,
    selectedPageId,
    selectedPanelId,
    zoom,
  });
}

export function ComicPageEditor() {
  const { projectId = "demo" } = useParams();
  const navigate = useNavigate();
  const realProject = UUID_PATTERN.test(projectId);

  const initialStory = useMemo(
    () => defaultStoryPlan(projectId),
    [projectId],
  );
  const initialCover = useMemo(defaultCover, []);
  const initialStoryPage = useMemo(
    () => makeStoryPage(1, initialStory.totalPages, fallbackLayouts),
    [initialStory.totalPages],
  );
  const initialPages = useMemo(
    () => synchronizeStoryPages(
      [coverAsPage(initialCover), initialStoryPage],
      initialStory.totalPages,
      fallbackLayouts,
    ),
    [initialCover, initialStory, initialStoryPage],
  );

  const [layouts, setLayouts] =
    useState<LayoutTemplate[]>(fallbackLayouts);
  const [pages, setPages] = useState<ComicPage[]>(initialPages);
  const [storyPlan, setStoryPlan] =
    useState<StoryPlan>(initialStory);
  const [cover, setCover] =
    useState<CoverDraft | null>(initialCover);
  const [compositions, setCompositions] =
    useState<CoverComposition[]>([]);
  const [preservationOptions, setPreservationOptions] =
    useState<PreservationOption[]>(defaultPreservationOptions);
  const [selectedPageId, setSelectedPageId] =
    useState(initialStoryPage.id);
  const [selectedPanelId, setSelectedPanelId] =
    useState(initialStoryPage.panels[0]?.id ?? "");
  const [zoom, setZoom] = useState(110);
  const [focusMode, setFocusMode] = useState(false);
  const [hideEditorPanels, setHideEditorPanels] = useState(false);
  const [continuityOpen, setContinuityOpen] = useState(false);
  const [continuityRows, setContinuityRows] =
    useState<ContinuityRow[]>([]);
  const [continuityIssues, setContinuityIssues] =
    useState<ContinuityIssue[]>([]);
  const [comparisonOpen, setComparisonOpen] = useState(false);
  const [productivityOpen, setProductivityOpen] = useState(false);
  const [editorialOpen, setEditorialOpen] = useState(false);
  const [activityStudioOpen, setActivityStudioOpen] = useState(false);
  const [feedbackStudioOpen, setFeedbackStudioOpen] = useState(false);
  const [deliveryStudioOpen, setDeliveryStudioOpen] = useState(false);
  const [productivityAnalysis, setProductivityAnalysis] =
    useState<ProductivityAnalysis | null>(null);
  const [candidateReference, setCandidateReference] =
    useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [saveState, setSaveState] = useState<
    "saved" | "dirty" | "saving" | "failed" | "offline"
  >("saved");
  const [statusMessage, setStatusMessage] = useState(
    "Editor pronto para planejar a HQ.",
  );

  const historyRef = useRef(
    createHistory(
      snapshotOf(
        pages,
        storyPlan,
        cover,
        selectedPageId,
        selectedPanelId,
        zoom,
      ),
    ),
  );
  const autosaveTimer = useRef<number | null>(null);
  const autosaveClientId = useRef(`comic-editor-${projectId}-${crypto.randomUUID()}`);
  const autosaveSequence = useRef(0);
  const applyingHistory = useRef(false);

  const storyPages = pages.filter(
    (page) => page.pageType === "STORY",
  );
  const selectedPage = pages.find(
    (page) => page.id === selectedPageId,
  );
  const selectedPanel = selectedPage?.panels.find(
    (panel) => panel.id === selectedPanelId,
  );
  const selectedIndex = Math.max(
    0,
    pages.findIndex((page) => page.id === selectedPageId),
  );
  const selectedLayoutId = selectedPage?.layoutTemplateId ?? undefined;
  const totalPanels = storyPages.reduce(
    (sum, page) => sum + page.panels.length,
    0,
  );

  useEffect(() => {
    setPages((current) => {
      const currentStoryTotal = current.filter(
        (page) => page.pageType === "STORY",
      ).length;
      if (currentStoryTotal === storyPlan.totalPages) return current;
      return synchronizeStoryPages(
        current,
        storyPlan.totalPages,
        layouts,
      );
    });
  }, [layouts, storyPlan.totalPages]);

  const recordHistory = useCallback(
    (
      nextPages: ComicPage[] = pages,
      nextStory: StoryPlan = storyPlan,
      nextCover: CoverDraft | null = cover,
      nextPageId: string = selectedPageId,
      nextPanelId: string = selectedPanelId,
      nextZoom: number = zoom,
    ) => {
      if (applyingHistory.current) return;
      historyRef.current = pushHistory(
        historyRef.current,
        snapshotOf(
          nextPages,
          nextStory,
          nextCover,
          nextPageId,
          nextPanelId,
          nextZoom,
        ),
      );
      setSaveState("dirty");
    },
    [
      cover,
      pages,
      selectedPageId,
      selectedPanelId,
      storyPlan,
      zoom,
    ],
  );

  function applySnapshot(snapshot: EditorSnapshot): void {
    applyingHistory.current = true;
    setPages(snapshot.pages);
    setStoryPlan(snapshot.storyPlan);
    setCover(snapshot.cover);
    setSelectedPageId(snapshot.selectedPageId);
    setSelectedPanelId(snapshot.selectedPanelId);
    setZoom(snapshot.zoom);
    queueMicrotask(() => {
      applyingHistory.current = false;
    });
  }

  const undo = useCallback(() => {
    const result = undoHistory(historyRef.current);
    historyRef.current = result.history;
    if (result.snapshot) {
      applySnapshot(result.snapshot);
      setStatusMessage("Última alteração desfeita.");
      setSaveState("dirty");
    }
  }, []);

  const redo = useCallback(() => {
    const result = redoHistory(historyRef.current);
    historyRef.current = result.history;
    if (result.snapshot) {
      applySnapshot(result.snapshot);
      setStatusMessage("Alteração refeita.");
      setSaveState("dirty");
    }
  }, []);

  useEffect(() => {
    const onFocusChanged = (event: Event) => {
      const custom = event as CustomEvent<{ enabled: boolean }>;
      setFocusMode(Boolean(custom.detail?.enabled));
    };
    window.addEventListener(
      "educode:focus-mode-changed",
      onFocusChanged as EventListener,
    );
    return () =>
      window.removeEventListener(
        "educode:focus-mode-changed",
        onFocusChanged as EventListener,
      );
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const editing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.tagName === "SELECT";
      if (event.ctrlKey && !event.shiftKey && event.key.toLowerCase() === "z") {
        if (editing) return;
        event.preventDefault();
        undo();
      }
      if (
        (event.ctrlKey && event.key.toLowerCase() === "y") ||
        (event.ctrlKey &&
          event.shiftKey &&
          event.key.toLowerCase() === "z")
      ) {
        if (editing) return;
        event.preventDefault();
        redo();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [redo, undo]);

  useEffect(() => {
    let active = true;

    async function load(): Promise<void> {
      if (!realProject) return;
      setStatusMessage("Carregando capa, páginas e preferências...");
      const results = await Promise.allSettled([
        comicPageEditorApi.listLayouts(),
        comicPageEditorApi.listPages(projectId),
        comicPageEditorApi.getStoryPlan(projectId),
        comicPageEditorApi.getCover(projectId),
        comicPageEditorApi.coverCompositions(),
        comicPageEditorApi.preservationOptions(),
        comicPageEditorApi.continuityMap(projectId),
      ]);
      if (!active) return;

      const loadedLayouts =
        results[0].status === "fulfilled"
          ? mergeLayouts(results[0].value)
          : fallbackLayouts;
      const loadedPages =
        results[1].status === "fulfilled"
          ? results[1].value
          : [];
      const loadedStory =
        results[2].status === "fulfilled"
          ? results[2].value
          : defaultStoryPlan(projectId);
      const loadedCover =
        results[3].status === "fulfilled"
          ? results[3].value
          : null;

      setLayouts(loadedLayouts);
      setStoryPlan(loadedStory);
      setCover(loadedCover);

      const normalizedPages = [
        ...(loadedCover ? [coverAsPage(loadedCover)] : []),
        ...loadedPages.filter((page) => page.pageType !== "COVER"),
      ];
      const finalPages = synchronizeStoryPages(
        normalizedPages.length
          ? normalizedPages
          : [
              coverAsPage(defaultCover()),
              makeStoryPage(1, loadedStory.totalPages, loadedLayouts),
            ],
        loadedStory.totalPages,
        loadedLayouts,
      );
      setPages(finalPages);

      const firstStory =
        finalPages.find((page) => page.pageType === "STORY") ??
        finalPages[0];
      setSelectedPageId(firstStory.id);
      setSelectedPanelId(firstStory.panels[0]?.id ?? "");

      if (results[4].status === "fulfilled") {
        setCompositions(results[4].value);
      }
      if (results[5].status === "fulfilled") {
        setPreservationOptions(results[5].value);
      }
      if (results[6].status === "fulfilled") {
        setContinuityRows(results[6].value.pages);
        setContinuityIssues(results[6].value.issues);
      }

      historyRef.current = createHistory(
        snapshotOf(
          finalPages,
          loadedStory,
          loadedCover,
          firstStory.id,
          firstStory.panels[0]?.id ?? "",
          zoom,
        ),
      );
      setSaveState("saved");
      setStatusMessage("Projeto carregado.");
    }

    void load().catch((error: unknown) => {
      if (!active) return;
      setStatusMessage(
        error instanceof Error
          ? error.message
          : "Não foi possível carregar o projeto.",
      );
    });

    return () => {
      active = false;
    };
  }, [projectId, realProject]);

  useEffect(() => {
    if (saveState !== "dirty") return;
    if (autosaveTimer.current !== null) {
      window.clearTimeout(autosaveTimer.current);
    }
    autosaveTimer.current = window.setTimeout(() => {
      void autosave();
    }, 2200);
    return () => {
      if (autosaveTimer.current !== null) {
        window.clearTimeout(autosaveTimer.current);
      }
    };
  }, [saveState, pages, storyPlan, cover, zoom]);

  async function autosave(): Promise<void> {
    setSaveState("saving");
    try {
      if (realProject) {
        const snapshot = snapshotOf(
          pages,
          storyPlan,
          cover,
          selectedPageId,
          selectedPanelId,
          zoom,
        );
        autosaveSequence.current += 1;
        await comicPageEditorApi.autosave(projectId, {
          clientId: autosaveClientId.current,
          sequence: autosaveSequence.current,
          snapshot,
          checksum: await sha256(snapshot),
        });
      } else {
        localStorage.setItem(
          `educode_hq_autosave_${projectId}`,
          JSON.stringify(
            snapshotOf(
              pages,
              storyPlan,
              cover,
              selectedPageId,
              selectedPanelId,
              zoom,
            ),
          ),
        );
      }
      setSaveState("saved");
    } catch {
      setSaveState(navigator.onLine ? "failed" : "offline");
    }
  }

  function updateStory(patch: Partial<StoryPlan>): void {
    const next = { ...storyPlan, ...patch };
    const pageCountChanged =
      patch.totalPages !== undefined &&
      patch.totalPages !== storyPlan.totalPages;
    const nextPages = pageCountChanged
      ? synchronizeStoryPages(pages, next.totalPages, layouts)
      : pages;
    let nextPageId = selectedPageId;
    let nextPanelId = selectedPanelId;
    if (!nextPages.some((page) => page.id === selectedPageId)) {
      const fallbackPage = [...nextPages]
        .reverse()
        .find((page) => page.pageType === "STORY") ?? nextPages[0];
      nextPageId = fallbackPage?.id ?? "";
      nextPanelId = fallbackPage?.panels[0]?.id ?? "";
      setSelectedPageId(nextPageId);
      setSelectedPanelId(nextPanelId);
    }
    setStoryPlan(next);
    if (pageCountChanged) {
      setPages(nextPages);
      setStatusMessage(
        `${next.totalPages} páginas narrativas disponíveis para configurar o grid.`,
      );
    }
    recordHistory(
      nextPages,
      next,
      cover,
      nextPageId,
      nextPanelId,
    );
  }

  function updatePanel(patch: Partial<ComicPanel>): void {
    const nextPages = pages.map((page) =>
      page.id !== selectedPageId
        ? page
        : {
            ...page,
            panels: page.panels.map((panel) =>
              panel.id === selectedPanelId
                ? { ...panel, ...patch }
                : panel,
            ),
          },
    );
    setPages(nextPages);
    recordHistory(nextPages);
  }

  function updateCover(patch: Partial<CoverDraft>): void {
    if (!cover) return;
    const nextCover = { ...cover, ...patch };
    setCover(nextCover);
    const nextPages = [
      coverAsPage(nextCover),
      ...pages.filter((page) => page.pageType !== "COVER"),
    ];
    setPages(nextPages);
    recordHistory(nextPages, storyPlan, nextCover);
  }

  async function saveCover(): Promise<void> {
    if (!cover) return;
    setBusy(true);
    try {
      const saved = realProject
        ? await comicPageEditorApi.saveCover(projectId, cover)
        : { ...cover, revisionNumber: cover.revisionNumber + 1 };
      setCover(saved);
      const nextPages = [
        coverAsPage(saved),
        ...pages.filter((page) => page.pageType !== "COVER"),
      ];
      setPages(nextPages);
      setSaveState("saved");
      setStatusMessage("Capa salva sem entrar na contagem narrativa.");
    } catch (error) {
      setStatusMessage(
        error instanceof Error ? error.message : "Falha ao salvar a capa.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function generateCover(): Promise<void> {
    if (!cover) return;
    setBusy(true);
    try {
      if (!realProject) {
        setCandidateReference(
          "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1000&q=80",
        );
        setComparisonOpen(true);
        setStatusMessage("Variação de demonstração pronta para comparação.");
        return;
      }
      const result = await comicPageEditorApi.generateCover(
        projectId,
        {
          compositionCode: cover.compositionCode,
          variationCount: 4,
          additionalInstructions: [
            `Disciplina: ${cover.discipline}`,
            `Tema: ${cover.theme}`,
            `Ano escolar: ${cover.schoolYear}`,
            `Resumo: ${storyPlan.shortSummary || storyPlan.fullScript.slice(0, 1200)}`,
          ].filter(Boolean).join("\n"),
        },
      );
      const generatedCover = {
        ...result.cover,
        coverGeneration: {
          ...result.cover.coverGeneration,
          aiRequestId: result.requestId,
          status: result.status,
        },
      };
      setCover(generatedCover);
      setPages((current) => [
        coverAsPage(generatedCover),
        ...current.filter((page) => page.pageType !== "COVER"),
      ]);
      setStatusMessage(result.message);
    } catch (error) {
      setStatusMessage(
        error instanceof Error ? error.message : "Falha ao gerar a capa.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function refreshContinuity(): Promise<void> {
    try {
      if (realProject) {
        const result = await comicPageEditorApi.continuityMap(projectId);
        setContinuityRows(result.pages);
        setContinuityIssues(result.issues);
      } else {
        const rows = pages.map((page) => ({
          pageId: page.id,
          pageNumber: page.pageNumber,
          pageType: page.pageType,
          ...page.continuityMetadata,
        })) as ContinuityRow[];
        setContinuityRows(rows);
        setContinuityIssues([]);
      }
      setContinuityOpen(true);
    } catch (error) {
      setStatusMessage(
        error instanceof Error
          ? error.message
          : "Falha ao analisar continuidade.",
      );
    }
  }

  async function applyLayout(layout: LayoutTemplate): Promise<void> {
    if (!selectedPage || selectedPage.pageType !== "STORY") {
      setStatusMessage("A capa e a contracapa não utilizam grids.");
      return;
    }

    const updatedPage = applyLayoutToStoryPage(selectedPage, layout);
    const localPanels = updatedPage.panels;
    let nextPages = pages.map((page) =>
      page.id === selectedPage.id ? updatedPage : page,
    );
    setPages(nextPages);
    setSelectedPanelId(localPanels[0]?.id ?? "");
    recordHistory(
      nextPages,
      storyPlan,
      cover,
      selectedPageId,
      localPanels[0]?.id ?? "",
    );

    if (
      realProject &&
      UUID_PATTERN.test(selectedPage.id) &&
      UUID_PATTERN.test(layout.id)
    ) {
      setBusy(true);
      try {
        const savedPanels = await comicPageEditorApi.applyLayout(
          selectedPage.id,
          layout.id,
        );
        nextPages = nextPages.map((page) =>
          page.id === selectedPage.id
            ? { ...page, panels: savedPanels }
            : page,
        );
        setPages(nextPages);
        setSelectedPanelId(savedPanels[0]?.id ?? "");
        setStatusMessage(`${layout.name} aplicado preservando o conteúdo.`);
      } catch (error) {
        setStatusMessage(
          error instanceof Error
            ? error.message
            : "Falha ao aplicar o grid.",
        );
      } finally {
        setBusy(false);
      }
    }
  }

  async function varyLayoutsWithAi(): Promise<void> {
    const availableLayouts = realProject
      ? layouts.filter((layout) => UUID_PATTERN.test(layout.id))
      : layouts;
    if (!availableLayouts.length) {
      setStatusMessage("Nenhum grid disponível para a distribuição automática.");
      return;
    }
    setBusy(true);
    const nextPages = varyStoryPageLayouts(
      pages,
      availableLayouts,
    );
    setPages(nextPages);
    recordHistory(nextPages);
    try {
      if (realProject) {
        const persisted = await Promise.all(
          nextPages
            .filter(
              (page) =>
                page.pageType === "STORY" &&
                UUID_PATTERN.test(page.id) &&
                page.layoutTemplateId &&
                UUID_PATTERN.test(page.layoutTemplateId),
            )
            .map(async (page) => ({
              pageId: page.id,
              panels: await comicPageEditorApi.applyLayout(
                page.id,
                page.layoutTemplateId as string,
              ),
            })),
        );
        const panelsByPage = new Map(
          persisted.map((item) => [item.pageId, item.panels]),
        );
        setPages((current) => current.map((page) =>
          panelsByPage.has(page.id)
            ? { ...page, panels: panelsByPage.get(page.id) ?? page.panels }
            : page,
        ));
      }
      setStatusMessage(
        `IA distribuiu grids variados em ${storyPages.length} páginas narrativas.`,
      );
    } catch (error) {
      setStatusMessage(
        error instanceof Error
          ? error.message
          : "Falha ao distribuir os grids automaticamente.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function saveStory(): Promise<void> {
    setBusy(true);
    try {
      const saved = realProject
        ? await comicPageEditorApi.saveStoryPlan(projectId, storyPlan)
        : {
            ...storyPlan,
            exists: true,
            revisionNumber: storyPlan.revisionNumber + 1,
          };
      setStoryPlan(saved);
      setSaveState("saved");
      setStatusMessage(`Roteiro salvo. Versão ${saved.revisionNumber}.`);
    } catch (error) {
      setStatusMessage(
        error instanceof Error ? error.message : "Falha ao salvar o roteiro.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function distributeStory(): Promise<void> {
    setBusy(true);
    try {
      if (!realProject) {
        const nextPages = synchronizeStoryPages(
          pages,
          storyPlan.totalPages,
          layouts,
        );
        setPages(nextPages);
        recordHistory(nextPages);
        setStatusMessage(
          `Estrutura preparada com ${storyPlan.totalPages} páginas narrativas.`,
        );
        return;
      }
      await comicPageEditorApi.saveStoryPlan(projectId, storyPlan);
      const result = await comicPageEditorApi.distributeStory(
        projectId,
        {
          ensureTotalPages: true,
          preserveExistingSummaries: false,
          applyLayoutRecommendations:
            storyPlan.distributionMode === "AUTOMATIC",
        },
      );
      const loaded = await comicPageEditorApi.listPages(projectId);
      const nextPages = [
        ...(cover ? [coverAsPage(cover)] : []),
        ...loaded.filter((page) => page.pageType !== "COVER"),
      ];
      setPages(synchronizeStoryPages(
        nextPages,
        result.storyPlan.totalPages,
        layouts,
      ));
      setStoryPlan(result.storyPlan);
      setStatusMessage(
        `Narrativa distribuída em ${result.pages} páginas e ${result.panels} quadros.`,
      );
    } catch (error) {
      setStatusMessage(
        error instanceof Error
          ? error.message
          : "Falha ao distribuir a narrativa.",
      );
    } finally {
      setBusy(false);
    }
  }


async function createBackCover(): Promise<void> {
  setBusy(true);
  try {
    if (realProject) {
      await comicPageEditorApi.createBackCover(projectId);
      const loaded = await comicPageEditorApi.listPages(projectId);
      setPages([
        ...(cover ? [coverAsPage(cover)] : []),
        ...loaded.filter((page) => page.pageType !== "COVER"),
      ]);
    } else if (!pages.some((page) => page.pageType === "BACK_COVER")) {
      setPages((current) => [
        ...current,
        {
          id: "demo-back-cover",
          pageNumber: 10001,
          pageType: "BACK_COVER",
          title: "Contracapa",
          status: "DRAFT",
          pageWidth: 1200,
          pageHeight: 1600,
          layoutTemplateId: null,
          backgroundSettings: {},
          accessibilitySettings: {},
          contentLayers: [],
          preservationSettings: {},
          continuityMetadata: {},
          coverGeneration: {},
          revisionNumber: 1,
          panels: [],
        },
      ]);
    }
    setStatusMessage("Contracapa criada fora da contagem narrativa.");
  } catch (error) {
    setStatusMessage(error instanceof Error ? error.message : "Falha ao criar a contracapa.");
  } finally {
    setBusy(false);
  }
}

  async function analyzeProductivity(): Promise<void> {
    setBusy(true);
    try {
      if (!realProject) {
        const story = pages.filter(
          (page) => page.pageType === "STORY",
        );
        const average =
          story.reduce(
            (sum, page) => sum + page.panels.length,
            0,
          ) / Math.max(1, story.length);
        setProductivityAnalysis({
          rhythm: {
            storyPages: story.length,
            expectedStoryPages: storyPlan.totalPages,
            averagePanelsPerPage: Number(average.toFixed(2)),
            warningCount: 0,
            status: "READY",
            warnings: [],
          },
          readability: {
            panels: [],
            ready: story.reduce(
              (sum, page) => sum + page.panels.length,
              0,
            ),
            warning: 0,
            blocked: 0,
          },
          publicationStatus: "READY",
        });
        return;
      }
      const result =
        await comicPageEditorApi.analyzeProductivity(
          projectId,
          storyPlan.totalPages,
        );
      setProductivityAnalysis(result);
      setStatusMessage(
        result.publicationStatus === "READY"
          ? "HQ pronta para publicação."
          : result.publicationStatus === "BLOCKED"
            ? "A análise encontrou impedimentos de legibilidade."
            : "A HQ está pronta com avisos para revisão.",
      );
    } catch (error) {
      setStatusMessage(
        error instanceof Error
          ? error.message
          : "Falha na análise de produtividade.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function moveStoryPage(
    pageId: string,
    direction: -1 | 1,
  ): Promise<void> {
    const story = pages.filter(
      (page) => page.pageType === "STORY",
    );
    const index = story.findIndex((page) => page.id === pageId);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= story.length) return;
    const reordered = [...story];
    [reordered[index], reordered[target]] = [
      reordered[target],
      reordered[index],
    ];
    const numbered = reordered.map((page, pageIndex) => ({
      ...page,
      pageNumber: pageIndex + 1,
    }));
    const nextPages = [
      ...pages.filter((page) => page.pageType === "COVER"),
      ...numbered,
      ...pages.filter(
        (page) =>
          !["COVER", "STORY"].includes(page.pageType),
      ),
    ];
    setPages(nextPages);
    recordHistory(nextPages);
    if (realProject) {
      await comicPageEditorApi.reorderStoryPages(
        projectId,
        numbered.map((page) => page.id),
        false,
      );
    }
  }

  async function movePanel(
    pageId: string,
    panelId: string,
    direction: -1 | 1,
  ): Promise<void> {
    const page = pages.find((item) => item.id === pageId);
    if (!page) return;
    const index = page.panels.findIndex(
      (panel) => panel.id === panelId,
    );
    const target = index + direction;
    if (index < 0 || target < 0 || target >= page.panels.length) return;
    const reordered = [...page.panels];
    [reordered[index], reordered[target]] = [
      reordered[target],
      reordered[index],
    ];
    const numbered = reordered.map((panel, panelIndex) => ({
      ...panel,
      panelOrder: panelIndex + 1,
      accessibilityMetadata: {
        ...(panel.accessibilityMetadata ?? {}),
        reading_order: panelIndex + 1,
      },
    }));
    const nextPages = pages.map((item) =>
      item.id === pageId
        ? { ...item, panels: numbered }
        : item,
    );
    setPages(nextPages);
    recordHistory(nextPages);
    if (realProject) {
      const saved = await comicPageEditorApi.reorderPanels(
        pageId,
        numbered.map((panel) => panel.id),
      );
      setPages((current) =>
        current.map((item) =>
          item.id === pageId
            ? { ...item, panels: saved }
            : item,
        ),
      );
    }
  }

  async function savePageLayout(pageId: string): Promise<void> {
    const page = pages.find((item) => item.id === pageId);
    if (!page) return;
    const name = window.prompt(
      "Nome do grid personalizado:",
      `Meu grid ${page.pageNumber}`,
    );
    if (!name) return;
    const code = `CUSTOM_${name
      .toUpperCase()
      .normalize("NFD")
      .replace(/[\\u0300-\\u036f]/g, "")
      .replace(/[^A-Z0-9]+/g, "_")
      .replace(/^_|_$/g, "")}_${Date.now()}`;
    try {
      if (realProject) {
        const layout =
          await comicPageEditorApi.saveCurrentPageAsLayout(
            pageId,
            {
              code,
              name,
              description: "Grid salvo pelo professor no editor.",
              category: "CUSTOM",
            },
          );
        setLayouts((current) => mergeLayouts([...current, layout]));
      }
      setStatusMessage(
        `Grid "${name}" salvo na biblioteca do professor.`,
      );
    } catch (error) {
      setStatusMessage(
        error instanceof Error
          ? error.message
          : "Falha ao salvar o grid personalizado.",
      );
    }
  }

  async function generateComic(): Promise<void> {
    if (!realProject) {
      setStatusMessage("Geração final disponível em projetos persistidos.");
      return;
    }
    setBusy(true);
    try {
      const job = await comicPageEditorApi.createGenerationJob(projectId);
      navigate(`/teacher/comic-studio/generation/${job.id}`);
    } catch (error) {
      setStatusMessage(
        error instanceof Error ? error.message : "Falha ao gerar a HQ.",
      );
      setBusy(false);
    }
  }

  function toggleFocus(): void {
    const enabled = !focusMode;
    setFocusMode(enabled);
    window.dispatchEvent(
      new CustomEvent("educode:set-focus-mode", {
        detail: { enabled },
      }),
    );
  }

  function selectPage(pageId: string): void {
    const page = pages.find((item) => item.id === pageId);
    setSelectedPageId(pageId);
    setSelectedPanelId(page?.panels[0]?.id ?? "");
  }

  function previousPage(): void {
    const page = pages[selectedIndex - 1];
    if (page) selectPage(page.id);
  }

  function nextPage(): void {
    const page = pages[selectedIndex + 1];
    if (page) selectPage(page.id);
  }

  const saveLabel = {
    saved: "Salvo agora",
    dirty: "Alterações não salvas",
    saving: "Salvando...",
    failed: "Falha ao salvar",
    offline: "Trabalhando offline",
  }[saveState];

  return (
    <main
      className={[
        "hq-editor-shell",
        focusMode ? "hq-editor-focus" : "",
        hideEditorPanels ? "hq-editor-panels-hidden" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <header className="hq-editor-toolbar">
        <div className="hq-brand-title">
          <span className="hq-eyebrow">EduCode Comic Studio</span>
          <h1>Editor visual de páginas</h1>
        </div>
        <div className="hq-toolbar-actions">
          <span className={`hq-save-state state-${saveState}`}>
            <b>{saveState === "saved" ? "✓" : "●"}</b>
            {saveLabel}
          </span>
          <button
            type="button"
            className="hq-undo-button"
            onClick={undo}
            title="Desfazer (Ctrl+Z)"
          >
            ↶ Desfazer
          </button>
          <button
            type="button"
            className="hq-undo-button"
            onClick={redo}
            title="Refazer (Ctrl+Y)"
          >
            ↷ Refazer
          </button>
          <button
            type="button"
            className="hq-focus-button"
            onClick={toggleFocus}
          >
            {focusMode ? "Sair do foco" : "Modo foco"}
          </button>
          <button
            type="button"
            className="hq-preview-button"
            onClick={() => setHideEditorPanels((value) => !value)}
          >
            {hideEditorPanels ? "Restaurar painéis" : "Ocultar painéis"}
          </button>
          <button type="button" className="hq-delivery-button" onClick={() => setDeliveryStudioOpen(true)}>
            ▶ Aplicar para turmas
          </button>
          <button
            type="button"
            className="hq-feedback-button"
            onClick={() => setFeedbackStudioOpen(true)}
          >
            ✓ Correção e feedback
          </button>
          <button
            type="button"
            className="hq-activity-button"
            onClick={() => setActivityStudioOpen(true)}
          >
            ◫ Atividades pós-HQ
          </button>
          <button
            type="button"
            className="hq-editorial-button"
            onClick={() => setEditorialOpen(true)}
          >
            ◉ Balões e revisão
          </button>
          <button
            type="button"
            className="hq-productivity-button"
            onClick={() => setProductivityOpen(true)}
          >
            ◇ Produtividade
          </button>
          <button
            type="button"
            className="hq-primary"
            disabled={busy}
            onClick={() => void generateComic()}
          >
            Gerar HQ ✦
          </button>
        </div>
      </header>

      <section className="hq-editor-workspace">
        <LayoutLibraryPanel
          layouts={layouts}
          selectedId={selectedLayoutId}
          onSelect={(layout) => void applyLayout(layout)}
          onAutoArrange={() => void varyLayoutsWithAi()}
          autoArrangeDisabled={busy || !storyPages.length}
        />

        <section className="hq-canvas-column">
          <div className="hq-canvas-topbar">
            <div className="hq-page-heading">
              <strong>
                {selectedPage?.pageType === "COVER"
                  ? "▰ Capa"
                  : selectedPage?.pageType === "BACK_COVER"
                    ? "▰ Contracapa"
                    : `▤ Página ${selectedPage?.pageNumber ?? 1}`}
              </strong>
              <span className="hq-ai-awareness">
                A capa fica fora das {storyPlan.totalPages} páginas
                narrativas. Atividades e gabaritos também terão contagem
                separada.
              </span>
            </div>

            <div className="hq-editor-controls">
              <label className="hq-control-chip">
                <span>▧ Páginas da história</span>
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={storyPlan.totalPages}
                  onChange={(event: ChangeEvent<HTMLInputElement>) =>
                    updateStory({
                      totalPages: Math.max(
                        1,
                        Number(event.target.value) || 1,
                      ),
                    })
                  }
                />
              </label>
              <label className="hq-control-chip">
                <span>◷ Ritmo</span>
                <select
                  value={storyPlan.narrativePacing}
                  onChange={(event: ChangeEvent<HTMLSelectElement>) =>
                    updateStory({
                      narrativePacing:
                        event.target.value as NarrativePacing,
                    })
                  }
                >
                  <option value="SLOW">Detalhado</option>
                  <option value="BALANCED">Equilibrado</option>
                  <option value="FAST">Ágil</option>
                  <option value="CINEMATIC">Cinematográfico</option>
                </select>
              </label>
              <label className="hq-control-chip hq-green-chip">
                <span>✦ Distribuição</span>
                <select
                  value={storyPlan.distributionMode}
                  onChange={(event: ChangeEvent<HTMLSelectElement>) =>
                    updateStory({
                      distributionMode:
                        event.target.value as DistributionMode,
                    })
                  }
                >
                  <option value="AUTOMATIC">Automática e variada</option>
                  <option value="ASSISTED">Assistida</option>
                  <option value="MANUAL">Manual</option>
                </select>
              </label>
              <button
                type="button"
                className="hq-continuity-button"
                onClick={() => void refreshContinuity()}
              >
                ◈ Mapa de continuidade
              </button>
            </div>

            <div className="hq-zoom-control">
              <span>Zoom da página</span>
              <div>
                <button
                  type="button"
                  onClick={() => {
                    const next = Math.max(60, zoom - 10);
                    setZoom(next);
                    recordHistory(
                      pages,
                      storyPlan,
                      cover,
                      selectedPageId,
                      selectedPanelId,
                      next,
                    );
                  }}
                >
                  −
                </button>
                <output>{zoom}%</output>
                <button
                  type="button"
                  onClick={() => {
                    const next = Math.min(160, zoom + 10);
                    setZoom(next);
                    recordHistory(
                      pages,
                      storyPlan,
                      cover,
                      selectedPageId,
                      selectedPanelId,
                      next,
                    );
                  }}
                >
                  +
                </button>
              </div>
              <input
                type="range"
                min={60}
                max={160}
                step={5}
                value={zoom}
                onChange={(event: ChangeEvent<HTMLInputElement>) =>
                  setZoom(Number(event.target.value))
                }
              />
            </div>
          </div>

          <div className="hq-status-banner">
            <span>{statusMessage}</span>
            <small>
              1 capa · {storyPages.length} página(s) de história ·{" "}
              {totalPanels} quadro(s) · zoom preservado em {zoom}%
            </small>
          </div>

          {selectedPage?.pageType === "COVER" && cover ? (
            <CoverEditor
              cover={cover}
              compositions={compositions}
              zoom={zoom}
              busy={busy}
              onChange={updateCover}
              onChangeLayer={(layerId, patch) =>
                updateCover({
                  contentLayers: cover.contentLayers.map((layer) =>
                    layer.id === layerId
                      ? { ...layer, ...patch }
                      : layer,
                  ),
                })
              }
              onSave={() => void saveCover()}
              onGenerate={() => void generateCover()}
              onApplyReadyResult={() => setComparisonOpen(true)}
              onCreateBackCover={() => void createBackCover()}
            />
          ) : selectedPage?.pageType === "STORY" ? (
            <PagePreviewCanvas
              page={selectedPage}
              selectedPanelId={selectedPanelId}
              zoom={zoom}
              onSelectPanel={setSelectedPanelId}
            />
          ) : (
            <div className="hq-special-page-editor">
              <strong>
                {selectedPage?.pageType === "BACK_COVER"
                  ? "Contracapa"
                  : "Página especial"}
              </strong>
              <p>
                Esta página não utiliza grids e não participa da
                distribuição narrativa.
              </p>
            </div>
          )}

          <PageThumbnailStrip
            pages={pages}
            selectedPageId={selectedPageId}
            onSelect={selectPage}
            onPrevious={previousPage}
            onNext={nextPage}
          />
        </section>

        <PanelInspector
          panel={
            selectedPage?.pageType === "STORY"
              ? selectedPanel
              : undefined
          }
          panelCount={
            selectedPage?.pageType === "STORY"
              ? selectedPage.panels.length
              : 0
          }
          storyPlan={storyPlan}
          preservationOptions={preservationOptions}
          busy={busy}
          onChangeStoryPlan={updateStory}
          onChangePanel={updatePanel}
          onSaveStory={() => void saveStory()}
          onGenerateStory={() =>
            setStatusMessage(
              "A geração por IA usa as páginas e os grids reais da HQ.",
            )
          }
          onDistributeStory={() => void distributeStory()}
          onSavePanel={() =>
            setStatusMessage("Quadro incluído no próximo autosave.")
          }
          onRegenerate={() =>
            setStatusMessage(
              "A nova imagem será comparada antes de substituir a atual.",
            )
          }
          onLock={(key) => {
            if (!selectedPanel) return;
            updatePanel({
              lockedElements: selectedPanel.lockedElements.includes(key)
                ? selectedPanel.lockedElements.filter(
                    (item) => item !== key,
                  )
                : [...selectedPanel.lockedElements, key],
            });
          }}
        />
      </section>

      <ContinuityPanel
        open={continuityOpen}
        rows={continuityRows}
        issues={continuityIssues}
        onClose={() => setContinuityOpen(false)}
        onEdit={(row) => {
          selectPage(row.pageId);
          setContinuityOpen(false);
        }}
      />

      <DeliveryStudio
        open={deliveryStudioOpen}
        projectId={projectId}
        onClose={() => setDeliveryStudioOpen(false)}
      />

      <FeedbackStudio
        open={feedbackStudioOpen}
        projectId={projectId}
        onClose={() => setFeedbackStudioOpen(false)}
      />

      <ActivityStudio
        open={activityStudioOpen}
        projectId={projectId}
        pages={pages}
        selectedPageId={selectedPage?.id}
        selectedPanelId={selectedPanel?.id}
        onClose={() => setActivityStudioOpen(false)}
        onCreated={() => {
          setStatusMessage(
            "Atividade criada e vinculada ao Assessment Hub.",
          );
          if (realProject) {
            void comicPageEditorApi.listPages(projectId).then((loaded) => {
              setPages([
                ...(cover ? [coverAsPage(cover)] : []),
                ...loaded.filter((page) => page.pageType !== "COVER"),
              ]);
            });
          }
        }}
      />

      <EditorialPanel
        open={editorialOpen}
        projectId={projectId}
        panelId={selectedPanel?.id}
        pageId={selectedPage?.id}
        schoolYear={cover?.schoolYear ?? ""}
        onClose={() => setEditorialOpen(false)}
      />

      <ProductivityPanel
        open={productivityOpen}
        pages={pages}
        analysis={productivityAnalysis}
        busy={busy}
        onClose={() => setProductivityOpen(false)}
        onAnalyze={() => void analyzeProductivity()}
        onMovePage={(pageId, direction) =>
          void moveStoryPage(pageId, direction)
        }
        onMovePanel={(pageId, panelId, direction) =>
          void movePanel(pageId, panelId, direction)
        }
        onSaveLayout={(pageId) => void savePageLayout(pageId)}
      />

      <ComparisonDialog
        open={comparisonOpen}
        title="Comparar variações da capa"
        originalReference={cover?.backgroundAssetReference}
        candidateReference={candidateReference}
        onKeepOriginal={() => setComparisonOpen(false)}
        onGenerateAgain={() => void generateCover()}
        onApplyCandidate={() => {
          if (candidateReference) {
            updateCover({
              backgroundAssetReference: candidateReference,
            });
          }
          setComparisonOpen(false);
          setStatusMessage("Nova arte aplicada após confirmação.");
        }}
      />
    </main>
  );
}
