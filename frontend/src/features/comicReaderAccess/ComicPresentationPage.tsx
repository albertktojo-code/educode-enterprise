import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { comicReaderApi } from "./api";
import { ReaderSurface } from "./ReaderSurface";
import type { PresentationState, ReaderManifest, ReaderPreferences } from "./types";
import "./styles.css";

const PRESENTATION_PREFERENCES: ReaderPreferences = {
  reader_mode: "PANEL",
  font_scale: 1.15,
  line_spacing: 1.5,
  high_contrast: false,
  reduced_motion: false,
  screen_reader_mode: false,
  show_alt_text: false,
  auto_play_narration: false,
  caption_mode: "VISIBLE",
  focus_mode: true,
  narration_rate: 1,
  zoom_level: 1,
  orientation: "AUTO",
};

export function ComicPresentationPage() {
  const { presentationId = "" } = useParams();
  const [state, setState] = useState<PresentationState | null>(null);
  const [manifest, setManifest] = useState<ReaderManifest | null>(null);
  const [message, setMessage] = useState("Carregando apresentação...");

  useEffect(() => {
    comicReaderApi
      .presentation(presentationId)
      .then(async (value) => {
        setState(value);
        setManifest(await comicReaderApi.manifest(value.release_id));
        setMessage("");
      })
      .catch((error: Error) => setMessage(error.message));
  }, [presentationId]);

  async function transition(target: string) {
    if (!state) return;
    try {
      setState(
        await comicReaderApi.transitionPresentation(
          state.id,
          target,
          state.revision,
        ),
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao controlar apresentação.");
    }
  }

  async function move(delta: number) {
    if (!state || !manifest) return;
    let page = Math.max(1, state.current_page);
    let panel = Math.max(1, state.current_panel + delta);
    const currentPanels = manifest.pages[page - 1]?.panels?.length ?? 0;

    if (panel > currentPanels && page < manifest.pages.length) {
      page += 1;
      panel = 1;
    } else if (panel < 1 && page > 1) {
      page -= 1;
      panel = manifest.pages[page - 1]?.panels?.length ?? 1;
    }

    try {
      setState(
        await comicReaderApi.advancePresentation(state.id, {
          page_number: page,
          panel_number: panel,
          reveal_step: state.reveal_step + 1,
          presenter_note: state.presenter_note,
          expected_revision: state.revision,
        }),
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao avançar apresentação.");
    }
  }

  if (!state || !manifest) {
    return <section><p>{message}</p></section>;
  }

  return (
    <section className="presentation-page">
      <header className="presentation-header">
        <div>
          <Link to="/comic-reader">← HQs</Link>
          <h1>{state.title}</h1>
          <p>
            Código de entrada: <strong className="presentation-code">{state.join_code}</strong>
          </p>
        </div>
        <div className="button-row">
          {state.status === "DRAFT" ? (
            <button type="button" onClick={() => void transition("LIVE")}>Iniciar</button>
          ) : null}
          {state.status === "LIVE" ? (
            <button type="button" onClick={() => void transition("PAUSED")}>Pausar</button>
          ) : null}
          {state.status === "PAUSED" ? (
            <button type="button" onClick={() => void transition("LIVE")}>Retomar</button>
          ) : null}
          {!["ENDED", "CANCELLED"].includes(state.status) ? (
            <button type="button" onClick={() => void transition("ENDED")}>Encerrar</button>
          ) : null}
        </div>
      </header>

      {message ? <div className="inline-message">{message}</div> : null}

      <ReaderSurface
        pages={manifest.pages}
        pageIndex={Math.max(0, state.current_page - 1)}
        panelIndex={Math.max(0, state.current_panel - 1)}
        mode="PANEL"
        preferences={PRESENTATION_PREFERENCES}
      />

      <footer className="presentation-controls">
        <button type="button" onClick={() => void move(-1)}>Quadro anterior</button>
        <span>
          Página {state.current_page} · Quadro {Math.max(1, state.current_panel)}
          {" · "}{state.status}
        </span>
        <button type="button" onClick={() => void move(1)}>Próximo quadro</button>
      </footer>
    </section>
  );
}
