import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { Link, useParams } from "react-router-dom";

import { AccessibilityToolbar } from "./AccessibilityToolbar";
import { comicReaderApi } from "./api";
import { ReaderSurface } from "./ReaderSurface";
import {
  flushReaderEvents,
  trackReaderEvent,
} from "../comicReaderAnalytics/tracker";
import type {
  ReaderBookmark,
  ReaderManifest,
  ReaderPanel,
  ReaderPreferences,
} from "./types";
import "./styles.css";

const DEFAULT_PREFERENCES: ReaderPreferences = {
  reader_mode: "PAGE",
  font_scale: 1,
  line_spacing: 1.4,
  high_contrast: false,
  reduced_motion: false,
  screen_reader_mode: false,
  show_alt_text: false,
  auto_play_narration: false,
  caption_mode: "VISIBLE",
  focus_mode: false,
  narration_rate: 1,
  zoom_level: 1,
  orientation: "AUTO",
};

function orderPanels(panels: ReaderPanel[] | undefined): ReaderPanel[] {
  return [...(panels ?? [])].sort(
    (left, right) => (left.reading_order ?? 0) - (right.reading_order ?? 0),
  );
}

export function ComicReaderPage() {
  const { releaseId = "" } = useParams();
  const [manifest, setManifest] = useState<ReaderManifest | null>(null);
  const [preferences, setPreferences] = useState<ReaderPreferences>(DEFAULT_PREFERENCES);
  const [bookmarks, setBookmarks] = useState<ReaderBookmark[]>([]);
  const [pageIndex, setPageIndex] = useState(0);
  const [panelIndex, setPanelIndex] = useState(0);
  const [sequence, setSequence] = useState(0);
  const [message, setMessage] = useState("Carregando HQ...");
  const [analyticsSessionKey] = useState<string>(() => crypto.randomUUID());
  const startedAt = useRef(Date.now());
  const positionStartedAt = useRef(Date.now());

  useEffect(() => {
    Promise.all([
      comicReaderApi.manifest(releaseId),
      comicReaderApi.preferences(),
      comicReaderApi.checkpoint(releaseId),
      comicReaderApi.bookmarks(releaseId),
    ])
      .then(([manifestData, preferenceData, checkpoint, bookmarkData]) => {
        setManifest(manifestData);
        setPreferences(preferenceData);
        setPageIndex(Math.max(0, checkpoint.page_number - 1));
        setPanelIndex(Math.max(0, checkpoint.panel_number - 1));
        setSequence(checkpoint.last_sequence);
        setBookmarks(bookmarkData);
        setMessage("");
      })
      .catch((error: Error) => setMessage(error.message));
  }, [releaseId]);

  useEffect(() => {
    if (!manifest) return undefined;
    trackReaderEvent({
      release_id: manifest.release.id,
      session_key: analyticsSessionKey,
      event_type: "SESSION_STARTED",
      page_number: pageIndex + 1,
      panel_number: panelIndex + 1,
      sequence,
      properties: { reader_mode: preferences.reader_mode },
    });
    return () => {
      trackReaderEvent({
        release_id: manifest.release.id,
        session_key: analyticsSessionKey,
        event_type: "SESSION_ENDED",
        page_number: pageIndex + 1,
        panel_number: panelIndex + 1,
        duration_ms: Date.now() - startedAt.current,
        sequence,
        properties: { reader_mode: preferences.reader_mode },
      });
      void flushReaderEvents();
    };
  }, [analyticsSessionKey, manifest?.release.id]);

  useEffect(() => {
    if (!manifest) return undefined;
    positionStartedAt.current = Date.now();
    const panelMode =
      preferences.reader_mode === "PANEL" || preferences.reader_mode === "FOCUS";
    trackReaderEvent({
      release_id: manifest.release.id,
      session_key: analyticsSessionKey,
      event_type: panelMode ? "PANEL_VIEWED" : "PAGE_VIEWED",
      page_number: pageIndex + 1,
      panel_number: panelMode ? panelIndex + 1 : undefined,
      sequence,
      properties: { reader_mode: preferences.reader_mode },
    });
    return () => {
      trackReaderEvent({
        release_id: manifest.release.id,
        session_key: analyticsSessionKey,
        event_type: "POSITION_DWELL",
        page_number: pageIndex + 1,
        panel_number: panelMode ? panelIndex + 1 : undefined,
        duration_ms: Date.now() - positionStartedAt.current,
        sequence,
        properties: { reader_mode: preferences.reader_mode },
      });
    };
  }, [
    analyticsSessionKey,
    manifest?.release.id,
    pageIndex,
    panelIndex,
    preferences.reader_mode,
  ]);

  const currentPage = manifest?.pages[pageIndex];
  const panels = useMemo(
    () => orderPanels(currentPage?.panels),
    [currentPage],
  );

  const narrationText = useMemo(() => {
    const panel = panels[panelIndex];
    const track = manifest?.narrations.find(
      (item) =>
        item.page_number === pageIndex + 1 &&
        (item.panel_number == null || item.panel_number === panelIndex + 1),
    );
    if (track?.transcript) return track.transcript;
    if (!panel) return currentPage?.title ?? manifest?.release.release_name ?? "";
    return [
      panel.audio_description,
      panel.alt_text,
      panel.scene_description,
      ...(panel.balloons ?? []).map((balloon) =>
        `${balloon.speaker_name_snapshot ? `${balloon.speaker_name_snapshot}: ` : ""}${balloon.text ?? ""}`,
      ),
    ]
      .filter((value): value is string => Boolean(value))
      .join(". ");
  }, [currentPage, manifest, pageIndex, panelIndex, panels]);

  useEffect(() => {
    if (!manifest || !preferences.auto_play_narration || !narrationText) return undefined;
    narrate();
    return () => window.speechSynthesis.cancel();
  }, [manifest?.release.id, narrationText, preferences.auto_play_narration, preferences.narration_rate]);

  async function persist(
    nextPage: number,
    nextPanel: number,
    nextPreferences: ReaderPreferences = preferences,
  ) {
    const nextSequence = sequence + 1;
    setSequence(nextSequence);
    const completedPanels =
      manifest?.pages
        .slice(0, nextPage)
        .reduce((total, page) => total + (page.panels?.length ?? 0), 0) ?? 0;

    try {
      await comicReaderApi.saveCheckpoint(releaseId, {
        page_number: nextPage + 1,
        panel_number: nextPanel + 1,
        completed_panels: completedPanels,
        elapsed_seconds: Math.floor((Date.now() - startedAt.current) / 1000),
        sequence: nextSequence,
        reader_mode: nextPreferences.reader_mode,
        state: {},
      });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao salvar progresso.");
    }
  }

  async function updatePreferences(next: ReaderPreferences) {
    setPreferences(next);
    if (manifest) {
      trackReaderEvent({
        release_id: manifest.release.id,
        session_key: analyticsSessionKey,
        event_type: "ACCESSIBILITY_CHANGED",
        page_number: pageIndex + 1,
        panel_number: panelIndex + 1,
        sequence,
        properties: { ...next },
      });
    }
    try {
      await comicReaderApi.savePreferences(next);
      await persist(pageIndex, panelIndex, next);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao salvar preferências.");
    }
  }

  function trackCurrentCompletion(): void {
    if (!manifest) return;
    const panelMode =
      preferences.reader_mode === "PANEL" || preferences.reader_mode === "FOCUS";
    trackReaderEvent({
      release_id: manifest.release.id,
      session_key: analyticsSessionKey,
      event_type: panelMode ? "PANEL_COMPLETED" : "PAGE_COMPLETED",
      page_number: pageIndex + 1,
      panel_number: panelMode ? panelIndex + 1 : undefined,
      sequence,
      properties: { reader_mode: preferences.reader_mode },
    });
  }

  function next() {
    if (!manifest) return;
    trackCurrentCompletion();
    if (
      (preferences.reader_mode === "PANEL" || preferences.reader_mode === "FOCUS") &&
      panelIndex < panels.length - 1
    ) {
      const value = panelIndex + 1;
      setPanelIndex(value);
      void persist(pageIndex, value);
      return;
    }
    if (pageIndex < manifest.pages.length - 1) {
      const value = pageIndex + 1;
      setPageIndex(value);
      setPanelIndex(0);
      void persist(value, 0);
    }
  }

  function previous() {
    if (
      (preferences.reader_mode === "PANEL" || preferences.reader_mode === "FOCUS") &&
      panelIndex > 0
    ) {
      const value = panelIndex - 1;
      setPanelIndex(value);
      void persist(pageIndex, value);
      return;
    }
    if (pageIndex > 0) {
      const value = pageIndex - 1;
      setPageIndex(value);
      setPanelIndex(0);
      void persist(value, 0);
    }
  }

  function narrate() {
    if (!manifest) return;
    const analyticsReleaseId = manifest.release.id;
    window.speechSynthesis.cancel();
    const narrationStartedAt = Date.now();
    trackReaderEvent({
      release_id: analyticsReleaseId,
      session_key: analyticsSessionKey,
      event_type: "NARRATION_STARTED",
      page_number: pageIndex + 1,
      panel_number: panelIndex + 1,
      sequence,
      properties: { rate: preferences.narration_rate },
    });
    const utterance = new SpeechSynthesisUtterance(narrationText);
    utterance.lang = "pt-BR";
    utterance.rate = preferences.narration_rate;
    utterance.onend = () => {
      trackReaderEvent({
        release_id: analyticsReleaseId,
        session_key: analyticsSessionKey,
        event_type: "NARRATION_COMPLETED",
        page_number: pageIndex + 1,
        panel_number: panelIndex + 1,
        duration_ms: Date.now() - narrationStartedAt,
        sequence,
        properties: { rate: preferences.narration_rate },
      });
    };
    window.speechSynthesis.speak(utterance);
  }

  async function addBookmark() {
    if (!manifest) return;
    const analyticsReleaseId = manifest.release.id;
    try {
      await comicReaderApi.addBookmark(releaseId, {
        page_number: pageIndex + 1,
        panel_number:
          preferences.reader_mode === "PANEL" || preferences.reader_mode === "FOCUS"
            ? panelIndex + 1
            : undefined,
        label: `Página ${pageIndex + 1}`,
        note: "",
      });
      setBookmarks(await comicReaderApi.bookmarks(releaseId));
      trackReaderEvent({
        release_id: analyticsReleaseId,
        session_key: analyticsSessionKey,
        event_type: "BOOKMARK_CREATED",
        page_number: pageIndex + 1,
        panel_number: panelIndex + 1,
        sequence,
        properties: {},
      });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao criar marcador.");
    }
  }

  if (!manifest) {
    return <section><p>{message}</p></section>;
  }

  const glossary = manifest.glossary.filter(
    (item) => item.page_number == null || item.page_number === pageIndex + 1,
  );
  const assessments = manifest.assessment_links.filter(
    (item) =>
      item.page_number === pageIndex + 1 &&
      (item.panel_number == null || item.panel_number === panelIndex + 1),
  );

  const style = {
    "--reader-font-scale": preferences.font_scale,
    "--reader-line-spacing": preferences.line_spacing,
    "--reader-zoom": preferences.zoom_level,
  } as CSSProperties;

  return (
    <section
      className={[
        "comic-reader-page",
        preferences.high_contrast ? "reader-high-contrast" : "",
        preferences.reduced_motion ? "reader-reduced-motion" : "",
        preferences.reader_mode === "FOCUS" || preferences.focus_mode
          ? "reader-focus"
          : "",
        `reader-orientation-${preferences.orientation.toLowerCase()}`,
        preferences.screen_reader_mode ? "reader-screen-reader" : "",
      ].join(" ")}
      style={style}
    >
      <header className="page-header">
        <div>
          <Link to="/comic-reader">← Biblioteca de HQs</Link>
          <h1>{manifest.release.release_name}</h1>
          <p>
            Página {pageIndex + 1} de {manifest.pages.length}
            {preferences.reader_mode === "PANEL" || preferences.reader_mode === "FOCUS"
              ? ` · Quadro ${panelIndex + 1} de ${panels.length}`
              : ""}
          </p>
        </div>
        <button type="button" onClick={() => void addBookmark()}>
          Marcar posição
        </button>
      </header>

      {message ? <div className="inline-message">{message}</div> : null}

      <AccessibilityToolbar
        preferences={preferences}
        onChange={(value) => void updatePreferences(value)}
        onNarrate={narrate}
        onStopNarration={() => window.speechSynthesis.cancel()}
      />

      <div className="reader-workspace">
        <main>
          <ReaderSurface
            pages={manifest.pages}
            pageIndex={pageIndex}
            panelIndex={panelIndex}
            mode={preferences.reader_mode}
            preferences={preferences}
          />
          {preferences.reader_mode !== "VERTICAL" ? (
            <div className="reader-navigation">
              <button
                type="button"
                onClick={previous}
                disabled={pageIndex === 0 && panelIndex === 0}
              >
                Anterior
              </button>
              <button type="button" onClick={next}>Próximo</button>
            </div>
          ) : null}
        </main>

        <aside className="reader-side">
          <section className="panel">
            <h2>Glossário</h2>
            {glossary.length ? (
              glossary.map((item) => (
                <details
                  key={item.id}
                  onToggle={(event) => {
                    if (event.currentTarget.open) {
                      trackReaderEvent({
                        release_id: manifest.release.id,
                        session_key: analyticsSessionKey,
                        event_type: "GLOSSARY_OPENED",
                        page_number: pageIndex + 1,
                        panel_number: panelIndex + 1,
                        sequence,
                        properties: { term_id: item.id, term: item.term },
                      });
                    }
                  }}
                >
                  <summary>{item.term}</summary>
                  <p>{item.simplified_definition || item.definition}</p>
                </details>
              ))
            ) : (
              <p>Nenhum termo contextual nesta página.</p>
            )}
          </section>

          <section className="panel">
            <h2>Atividades relacionadas</h2>
            {assessments.length ? (
              assessments.map((item) => (
                <article key={item.id} className="reader-assessment">
                  <strong>{item.question?.title ?? "Questão vinculada"}</strong>
                  <p>{item.question?.prompt ?? ""}</p>
                  {item.assignment_id ? (
                    <Link
                      to={`/aluno/atividades/${item.assignment_id}`}
                      onClick={() =>
                        trackReaderEvent({
                          release_id: manifest.release.id,
                          session_key: analyticsSessionKey,
                          event_type: "ASSESSMENT_OPENED",
                          page_number: pageIndex + 1,
                          panel_number: panelIndex + 1,
                          sequence,
                          properties: {
                            assignment_id: item.assignment_id,
                            question_bank_item_id: item.question_bank_item_id,
                          },
                        })
                      }
                    >
                      Abrir atividade institucional
                    </Link>
                  ) : (
                    <small>A atividade ainda não foi publicada.</small>
                  )}
                </article>
              ))
            ) : (
              <p>Nenhuma atividade vinculada a esta posição.</p>
            )}
          </section>

          <section className="panel">
            <h2>Marcadores</h2>
            {bookmarks.length ? (
              bookmarks.map((item) => (
                <button
                  className="reader-bookmark"
                  key={item.id}
                  type="button"
                  onClick={() => {
                    setPageIndex(Math.max(0, item.page_number - 1));
                    setPanelIndex(Math.max(0, (item.panel_number ?? 1) - 1));
                  }}
                >
                  {item.label || `Página ${item.page_number}`}
                </button>
              ))
            ) : (
              <p>Você ainda não criou marcadores.</p>
            )}
          </section>
        </aside>
      </div>
    </section>
  );
}
