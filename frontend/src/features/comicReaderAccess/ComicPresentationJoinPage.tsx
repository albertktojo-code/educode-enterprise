import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useParams } from "react-router-dom";

import { comicReaderApi } from "./api";
import { ReaderSurface } from "./ReaderSurface";
import {
  flushReaderEvents,
  trackReaderEvent,
} from "../comicReaderAnalytics/tracker";
import type { PresentationState, ReaderManifest, ReaderPreferences } from "./types";
import "./styles.css";

const AUDIENCE_PREFERENCES: ReaderPreferences = {
  reader_mode: "PANEL",
  font_scale: 1,
  line_spacing: 1.4,
  high_contrast: false,
  reduced_motion: false,
  screen_reader_mode: false,
  show_alt_text: false,
  auto_play_narration: false,
  caption_mode: "VISIBLE",
  focus_mode: true,
  narration_rate: 1,
};

export function ComicPresentationJoinPage() {
  const route = useParams();
  const [code, setCode] = useState<string>(route.joinCode ?? "");
  const [state, setState] = useState<PresentationState | null>(null);
  const [manifest, setManifest] = useState<ReaderManifest | null>(null);
  const [message, setMessage] = useState("Informe o código exibido pelo professor.");
  const [analyticsSessionKey] = useState<string>(() => crypto.randomUUID());
  const stateRef = useRef<PresentationState | null>(null);
  const lastRevisionRef = useRef<number>(-1);

  async function join(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const value = await comicReaderApi.joinPresentation(code, AUDIENCE_PREFERENCES);
      setState(value);
      stateRef.current = value;
      lastRevisionRef.current = value.revision;
      setManifest(await comicReaderApi.manifest(value.release_id));
      trackReaderEvent({
        release_id: value.release_id,
        presentation_session_id: value.id,
        session_key: analyticsSessionKey,
        event_type: "PRESENTATION_JOINED",
        page_number: value.current_page,
        panel_number: Math.max(1, value.current_panel),
        sequence: value.revision,
        properties: { join_code: value.join_code },
      });
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao entrar na apresentação.");
    }
  }

  useEffect(() => {
    if (!state) return undefined;
    const joinCode = state.join_code;
    const timer = window.setInterval(() => {
      comicReaderApi
        .presentationByCode(joinCode)
        .then((next) => {
          if (next.revision !== lastRevisionRef.current) {
            trackReaderEvent({
              release_id: next.release_id,
              presentation_session_id: next.id,
              session_key: analyticsSessionKey,
              event_type: "PRESENTATION_SYNCED",
              page_number: next.current_page,
              panel_number: Math.max(1, next.current_panel),
              sequence: next.revision,
              properties: { status: next.status },
            });
            lastRevisionRef.current = next.revision;
          }
          stateRef.current = next;
          setState(next);
        })
        .catch((error: Error) => setMessage(error.message));
    }, 1500);
    return () => window.clearInterval(timer);
  }, [analyticsSessionKey, state?.id, state?.join_code]);

  useEffect(() => {
    return () => {
      const current = stateRef.current;
      if (!current) return;
      trackReaderEvent({
        release_id: current.release_id,
        presentation_session_id: current.id,
        session_key: analyticsSessionKey,
        event_type: "PRESENTATION_LEFT",
        page_number: current.current_page,
        panel_number: Math.max(1, current.current_panel),
        sequence: current.revision,
        properties: { status: current.status },
      });
      void comicReaderApi.leavePresentation(current.id);
      void flushReaderEvents();
    };
  }, [analyticsSessionKey]);

  if (!state || !manifest) {
    return (
      <section className="presentation-join">
        <form className="panel" onSubmit={(event) => void join(event)}>
          <h1>Entrar na apresentação</h1>
          <label>
            Código
            <input
              value={code}
              maxLength={20}
              onChange={(event) => setCode(event.target.value.toUpperCase())}
              autoFocus
            />
          </label>
          <button className="primary" type="submit">Entrar</button>
          <p>{message}</p>
        </form>
      </section>
    );
  }

  return (
    <section className="presentation-audience">
      <header className="presentation-header">
        <h1>{state.title}</h1>
        <span>
          {state.status === "PAUSED" ? "Apresentação pausada" : "Acompanhando professor"}
        </span>
      </header>
      <ReaderSurface
        pages={manifest.pages}
        pageIndex={Math.max(0, state.current_page - 1)}
        panelIndex={Math.max(0, state.current_panel - 1)}
        mode="PANEL"
        preferences={AUDIENCE_PREFERENCES}
      />
    </section>
  );
}
