import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import {
  studentExperienceApi,
  type StudentExperienceActivity,
  type StudentExperienceManifest,
} from "./api";
import {
  flushReaderEvents,
  trackReaderEvent,
} from "../comicReaderAnalytics/tracker";
import "./styles.css";

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String) : [];
}

function stringRecord(value: unknown): Record<string, string> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [key, String(item)]),
  );
}

function answerFromSaved(activity: StudentExperienceActivity): unknown {
  if (activity.activity_type === "MULTIPLE_CHOICE") {
    return stringList(activity.saved_response.selected_option_ids);
  }
  if (activity.activity_type === "TRUE_FALSE") {
    return activity.saved_response.answer;
  }
  if (activity.activity_type === "MATCHING") {
    const pairs = activity.saved_response.pairs;
    if (!Array.isArray(pairs)) return {};
    return Object.fromEntries(
      pairs
        .filter(
          (pair): pair is { left: unknown; right: unknown } =>
            Boolean(pair) &&
            typeof pair === "object" &&
            "left" in pair &&
            "right" in pair,
        )
        .map((pair) => [String(pair.left), String(pair.right)]),
    );
  }
  if (activity.activity_type === "ORDERING") {
    return stringList(activity.saved_response.items);
  }
  if (
    activity.activity_type === "FILL_BLANKS" ||
    activity.activity_type === "CROSSWORD"
  ) {
    return stringList(
      activity.saved_response.answers ?? activity.saved_response.words,
    );
  }
  if (activity.activity_type === "WORD_SEARCH") {
    return stringList(activity.saved_response.words).join(", ");
  }
  return activity.saved_response.text ?? "";
}

function responseFor(
  activity: StudentExperienceActivity,
  answer: unknown,
): Record<string, unknown> {
  if (activity.activity_type === "MULTIPLE_CHOICE") {
    return {
      selected_option_ids: stringList(answer).filter(Boolean),
    };
  }
  if (activity.activity_type === "TRUE_FALSE") {
    return { answer: answer === true };
  }
  if (activity.activity_type === "MATCHING") {
    return {
      pairs: Object.entries(stringRecord(answer)).map(([left, right]) => ({
        left,
        right,
      })),
    };
  }
  if (activity.activity_type === "ORDERING") {
    return { items: stringList(answer) };
  }
  if (activity.activity_type === "FILL_BLANKS") {
    return { answers: stringList(answer) };
  }
  if (activity.activity_type === "CROSSWORD") {
    return { words: stringList(answer) };
  }
  if (activity.activity_type === "WORD_SEARCH") {
    return {
      words: String(answer ?? "")
        .split(/[,\n;]/)
        .map((item) => item.trim())
        .filter(Boolean),
    };
  }
  return { text: String(answer ?? "") };
}

function hasAnswer(
  activity: StudentExperienceActivity,
  answer: unknown,
): boolean {
  if (activity.activity_type === "MULTIPLE_CHOICE") {
    return stringList(answer).length > 0;
  }
  if (activity.activity_type === "TRUE_FALSE") {
    return typeof answer === "boolean";
  }
  if (activity.activity_type === "MATCHING") {
    const values = Object.values(stringRecord(answer));
    return (
      values.length === (activity.activity_payload.left_items?.length ?? 0) &&
      values.every(Boolean)
    );
  }
  if (
    activity.activity_type === "ORDERING" ||
    activity.activity_type === "FILL_BLANKS" ||
    activity.activity_type === "CROSSWORD"
  ) {
    return stringList(answer).length > 0 &&
      stringList(answer).every((item) => item.trim());
  }
  return String(answer ?? "").trim().length > 0;
}

interface ActivityResponseEditorProps {
  activity: StudentExperienceActivity;
  answer: unknown;
  onChange: (answer: unknown) => void;
}

function ActivityResponseEditor({
  activity,
  answer,
  onChange,
}: ActivityResponseEditorProps) {
  if (activity.activity_type === "MULTIPLE_CHOICE") {
    const selected = stringList(answer);
    const multiple =
      activity.activity_payload.selection_mode === "MULTIPLE";
    return (
      <fieldset className="student-hq-options">
        <legend>Selecione {multiple ? "as alternativas" : "uma alternativa"}</legend>
        {(activity.activity_payload.options ?? []).map((option) => (
          <label key={option.id}>
            <input
              type={multiple ? "checkbox" : "radio"}
              name={`activity-${activity.id}`}
              value={option.id}
              checked={selected.includes(option.id)}
              onChange={() => {
                if (!multiple) {
                  onChange([option.id]);
                  return;
                }
                onChange(
                  selected.includes(option.id)
                    ? selected.filter((item) => item !== option.id)
                    : [...selected, option.id],
                );
              }}
            />
            {option.text}
          </label>
        ))}
      </fieldset>
    );
  }

  if (activity.activity_type === "TRUE_FALSE") {
    return (
      <fieldset className="student-hq-options">
        <legend>Escolha verdadeiro ou falso</legend>
        {[true, false].map((value) => (
          <label key={String(value)}>
            <input
              type="radio"
              name={`activity-${activity.id}`}
              checked={answer === value}
              onChange={() => onChange(value)}
            />
            {value ? "Verdadeiro" : "Falso"}
          </label>
        ))}
      </fieldset>
    );
  }

  if (activity.activity_type === "MATCHING") {
    const matches = stringRecord(answer);
    return (
      <div className="student-hq-structured-response" role="group" aria-label="Associação">
        {(activity.activity_payload.left_items ?? []).map((left) => (
          <label key={left.id}>
            {left.text}
            <select
              value={matches[left.text] ?? ""}
              onChange={(event) =>
                onChange({
                  ...matches,
                  [left.text]: event.target.value,
                })
              }
            >
              <option value="">Selecione a associação</option>
              {(activity.activity_payload.right_items ?? []).map((right) => (
                <option key={right.id} value={right.text}>
                  {right.text}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>
    );
  }

  if (activity.activity_type === "ORDERING") {
    const ordered = stringList(answer);
    return (
      <ol className="student-hq-ordering" aria-label="Ordem escolhida">
        {ordered.map((item, index) => (
          <li key={`${item}-${index}`}>
            <span>{item}</span>
            <button
              type="button"
              disabled={index === 0}
              aria-label={`Mover ${item} para cima`}
              onClick={() => {
                const updated = [...ordered];
                [updated[index - 1], updated[index]] = [
                  updated[index],
                  updated[index - 1],
                ];
                onChange(updated);
              }}
            >
              Subir
            </button>
            <button
              type="button"
              disabled={index === ordered.length - 1}
              aria-label={`Mover ${item} para baixo`}
              onClick={() => {
                const updated = [...ordered];
                [updated[index], updated[index + 1]] = [
                  updated[index + 1],
                  updated[index],
                ];
                onChange(updated);
              }}
            >
              Descer
            </button>
          </li>
        ))}
      </ol>
    );
  }

  if (
    activity.activity_type === "FILL_BLANKS" ||
    activity.activity_type === "CROSSWORD"
  ) {
    const values = stringList(answer);
    const prompts =
      activity.activity_type === "FILL_BLANKS"
        ? (activity.activity_payload.blanks ?? []).map((item) => ({
            id: item.id,
            label: item.label,
          }))
        : (activity.activity_payload.entries ?? []).map((item) => ({
            id: item.id,
            label: `${item.clue} (${item.length} letras)`,
          }));
    return (
      <div className="student-hq-structured-response" role="group" aria-label="Respostas">
        {prompts.map((prompt, index) => (
          <label key={prompt.id}>
            {prompt.label}
            <input
              value={values[index] ?? ""}
              onChange={(event) => {
                const updated = [...values];
                updated[index] = event.target.value;
                onChange(updated);
              }}
            />
          </label>
        ))}
      </div>
    );
  }

  if (activity.activity_type === "WORD_SEARCH") {
    return (
      <div className="student-hq-word-search">
        {activity.activity_payload.grid ? (
          <table>
            <caption>Grade do caça-palavras</caption>
            <tbody>
              {activity.activity_payload.grid.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {row.map((letter, columnIndex) => (
                    <td key={`${rowIndex}-${columnIndex}`}>{letter}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
        <p>
          Procure: {(activity.activity_payload.words ?? []).join(", ")}
        </p>
        <label>
          Palavras encontradas, separadas por vírgula
          <textarea
            value={String(answer ?? "")}
            onChange={(event) => onChange(event.target.value)}
          />
        </label>
      </div>
    );
  }

  return (
    <textarea
      aria-label={`Resposta para ${activity.title}`}
      value={String(answer ?? "")}
      onChange={(event) => onChange(event.target.value)}
      placeholder="Digite sua resposta."
    />
  );
}

export function HQStudentExperiencePage() {
  const { publicationId = "" } = useParams();
  const [manifest, setManifest] =
    useState<StudentExperienceManifest | null>(null);
  const [pageIndex, setPageIndex] = useState(0);
  const [activityIndex, setActivityIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [savedActivityIds, setSavedActivityIds] = useState<Set<string>>(
    new Set(),
  );
  const [highContrast, setHighContrast] = useState(false);
  const [fontScale, setFontScale] = useState(1);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const stateSequence = useRef(0);
  const autosaveSequence = useRef(0);
  const readerSessionKey = useRef(crypto.randomUUID());
  const readerEventSequence = useRef(0);

  useEffect(() => {
    void load();
  }, [publicationId]);

  async function load(): Promise<void> {
    setError("");
    setBusy(true);
    try {
      const loaded = await studentExperienceApi.manifest(publicationId);
      setManifest(loaded);
      setPageIndex(
        Math.max(
          0,
          loaded.pages.findIndex(
            (page) =>
              page.page_number === loaded.state.current_page_number,
          ),
        ),
      );
      setActivityIndex(loaded.state.current_activity_index);
      stateSequence.current = loaded.state.last_sequence;
      autosaveSequence.current = loaded.assessment.autosave_sequence;

      const restoredAnswers: Record<string, unknown> = {};
      const restoredIds = new Set<string>();
      loaded.activities.forEach((activity) => {
        if (activity.response_status === "ANSWERED") {
          restoredAnswers[activity.id] = answerFromSaved(activity);
          restoredIds.add(activity.id);
        } else if (activity.activity_type === "ORDERING") {
          restoredAnswers[activity.id] =
            activity.activity_payload.items ?? [];
        }
      });
      setAnswers(restoredAnswers);
      setSavedActivityIds(restoredIds);

      if (!loaded.assessment.session) {
        setMessage(
          loaded.assessment.can_start
            ? "Inicie a experiência quando estiver pronto."
            : "Não há tentativa disponível para esta aplicação.",
        );
      } else if (loaded.assessment.session.status === "PAUSED") {
        setMessage(
          "Esta tentativa está pausada. Procure o professor para retomá-la.",
        );
      }
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Não foi possível carregar a experiência.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function startExperience(): Promise<void> {
    if (!manifest?.assessment.can_start) return;
    setBusy(true);
    setError("");
    try {
      await studentExperienceApi.startSession(
        publicationId,
        manifest.assessment.student_id,
        manifest.assessment.target_id,
      );
      await load();
      setMessage("Experiência iniciada. O tempo da tentativa já está contando.");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Não foi possível iniciar a experiência.",
      );
      setBusy(false);
    }
  }

  const storyPages = useMemo(
    () =>
      (manifest?.pages ?? []).filter((page) =>
        ["COVER", "STORY", "BACK_COVER"].includes(page.page_type),
      ),
    [manifest],
  );

  const activity = manifest?.activities[activityIndex];
  const readingProgress = storyPages.length
    ? Math.round(((pageIndex + 1) / storyPages.length) * 100)
    : 100;
  const answeredCount = savedActivityIds.size;
  const activityProgress = manifest?.activities.length
    ? Math.round(
        (Math.min(manifest.activities.length, answeredCount) /
          manifest.activities.length) *
          100,
      )
    : 100;
  const sessionIsActive =
    manifest?.assessment.session?.status === "IN_PROGRESS";
  const currentPage = storyPages[pageIndex];

  useEffect(() => {
    const releaseId = manifest?.delivery.release_id;
    if (!releaseId || !sessionIsActive || !currentPage) return;

    const viewedAt = Date.now();
    readerEventSequence.current += 1;
    trackReaderEvent({
      release_id: releaseId,
      session_key: readerSessionKey.current,
      event_type: "PAGE_VIEWED",
      page_number: currentPage.page_number,
      sequence: readerEventSequence.current,
      properties: {
        source: "HQ_STUDENT_EXPERIENCE",
        publication_id: publicationId,
      },
    });
    return () => {
      readerEventSequence.current += 1;
      trackReaderEvent({
        release_id: releaseId,
        session_key: readerSessionKey.current,
        event_type: "POSITION_DWELL",
        page_number: currentPage.page_number,
        duration_ms: Math.max(0, Date.now() - viewedAt),
        sequence: readerEventSequence.current,
        properties: {
          source: "HQ_STUDENT_EXPERIENCE",
          publication_id: publicationId,
        },
      });
    };
  }, [
    currentPage,
    manifest?.delivery.release_id,
    publicationId,
    sessionIsActive,
  ]);

  useEffect(
    () => () => {
      void flushReaderEvents();
    },
    [],
  );

  async function persist(
    override: Partial<{
      pageIndex: number;
      activityIndex: number;
    }> = {},
  ): Promise<void> {
    const assessmentSessionId = manifest?.assessment.session?.id;
    if (!manifest || !assessmentSessionId) return;
    stateSequence.current += 1;
    const effectivePageIndex = override.pageIndex ?? pageIndex;
    const effectiveActivityIndex =
      override.activityIndex ?? activityIndex;
    const effectiveReadingProgress = storyPages.length
      ? Math.round(((effectivePageIndex + 1) / storyPages.length) * 100)
      : 100;
    const result = await studentExperienceApi.saveState(publicationId, {
      assessment_session_id: assessmentSessionId,
      current_page_number:
        storyPages[effectivePageIndex]?.page_number ?? 1,
      current_panel_number: 1,
      current_activity_index: effectiveActivityIndex,
      reading_progress: effectiveReadingProgress,
      activity_progress: activityProgress,
      answered_count: answeredCount,
      preferences: {
        high_contrast: highContrast,
        font_scale: fontScale,
        keyboard_navigation: true,
      },
      navigation_state: {
        active_tab:
          effectiveReadingProgress < 100 ? "READING" : "ACTIVITY",
      },
      last_feedback: {},
      sequence: stateSequence.current,
    });
    setMessage(
      result.current_stage === "COMPLETED"
        ? "Experiência concluída."
        : "Progresso salvo.",
    );
  }

  async function saveActivity(): Promise<void> {
    const assessmentSession = manifest?.assessment.session;
    if (!activity || !assessmentSession || !activity.session_item_id) {
      setError("A atividade não está vinculada à sessão canônica.");
      return;
    }
    if (!sessionIsActive) {
      setError("A tentativa não está ativa para receber respostas.");
      return;
    }
    const answer = answers[activity.id];
    if (!hasAnswer(activity, answer)) {
      setError("Informe uma resposta antes de salvar.");
      return;
    }

    setBusy(true);
    setError("");
    try {
      autosaveSequence.current += 1;
      await studentExperienceApi.autosaveResponse(
        assessmentSession.id,
        activity.session_item_id,
        autosaveSequence.current,
        responseFor(activity, answer),
      );
      setSavedActivityIds((current) => {
        const updated = new Set(current);
        updated.add(activity.id);
        return updated;
      });
      await persist();
      setMessage(
        "Resposta salva. A correção será realizada no envio final.",
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Não foi possível salvar a resposta.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function submitAssessment(): Promise<void> {
    const assessmentSession = manifest?.assessment.session;
    if (!assessmentSession || !sessionIsActive) return;
    if (answeredCount < (manifest?.activities.length ?? 0)) {
      setError("Salve uma resposta para todas as atividades antes de enviar.");
      return;
    }

    setBusy(true);
    setError("");
    try {
      await studentExperienceApi.submitSession(assessmentSession.id);
      setManifest((current) =>
        current?.assessment.session
          ? {
              ...current,
              assessment: {
                ...current.assessment,
                session: {
                  ...current.assessment.session,
                  status: "SUBMITTED",
                },
              },
            }
          : current,
      );
      await persist();
      setMessage(
        "Avaliação enviada. Respostas que exigem revisão seguirão para o professor.",
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Não foi possível enviar a avaliação.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!manifest) {
    return (
      <main className="student-hq-loading" aria-live="polite">
        {error || (busy ? "Carregando experiência…" : "Experiência indisponível.")}
      </main>
    );
  }

  if (!manifest.assessment.session) {
    return (
      <main className="student-hq-loading">
        <section aria-labelledby="student-hq-start-title">
          <h1 id="student-hq-start-title">{manifest.publication.title}</h1>
          <p aria-live="polite">{error || message}</p>
          <p>
            Tentativas: {manifest.assessment.attempts_used} de{" "}
            {manifest.assessment.attempts_allowed}.
          </p>
          {manifest.assessment.can_start ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => void startExperience()}
            >
              {busy ? "Iniciando…" : "Iniciar experiência"}
            </button>
          ) : null}
        </section>
      </main>
    );
  }

  const page = currentPage;

  return (
    <main
      className={`student-hq-shell ${
        highContrast ? "is-high-contrast" : ""
      }`}
      style={{ fontSize: `${fontScale}rem` }}
    >
      <header className="student-hq-header">
        <div>
          <span>Experiência digital do estudante</span>
          <h1>{manifest.publication.title}</h1>
        </div>
        <div className="student-hq-accessibility">
          <button
            type="button"
            aria-pressed={highContrast}
            onClick={() => setHighContrast((value) => !value)}
          >
            Alto contraste
          </button>
          <button
            type="button"
            aria-label="Aumentar fonte"
            onClick={() =>
              setFontScale((value) => Math.min(1.6, value + 0.1))
            }
          >
            A+
          </button>
          <button
            type="button"
            aria-label="Diminuir fonte"
            onClick={() =>
              setFontScale((value) => Math.max(0.8, value - 0.1))
            }
          >
            A−
          </button>
        </div>
      </header>

      <section className="student-hq-progress" aria-label="Progresso">
        <article>
          <b>História: {readingProgress}%</b>
          <progress max={100} value={readingProgress} />
        </article>
        <article>
          <b>Atividades: {activityProgress}%</b>
          <progress max={100} value={activityProgress} />
        </article>
        <article>
          <b>
            Respondidas: {answeredCount} de {manifest.activities.length}
          </b>
          <progress
            max={Math.max(1, manifest.activities.length)}
            value={answeredCount}
          />
        </article>
      </section>

      <div className="student-hq-content">
        <section className="student-hq-reader">
          <header>
            <h2>
              {page?.page_type === "COVER"
                ? "Capa"
                : `Página ${page?.page_number ?? 1}`}
            </h2>
            <span>{page?.title ?? ""}</span>
          </header>
          <div
            className="student-hq-page"
            tabIndex={0}
            aria-label={`Página ${page?.page_number ?? 1} da HQ`}
          >
            <strong>{page?.title || "Página da HQ"}</strong>
            <p>
              {String(
                page?.background_settings?.scene_summary ??
                  page?.background_settings?.theme ??
                  "Conteúdo visual da HQ.",
              )}
            </p>
            <small>
              Navegue pelas páginas com os botões anterior e próximo.
            </small>
          </div>
          <footer>
            <button
              type="button"
              disabled={pageIndex === 0}
              onClick={() => {
                const nextIndex = Math.max(0, pageIndex - 1);
                setPageIndex(nextIndex);
                void persist({ pageIndex: nextIndex });
              }}
            >
              Página anterior
            </button>
            <button
              type="button"
              disabled={pageIndex >= storyPages.length - 1}
              onClick={() => {
                const nextIndex = Math.min(
                  storyPages.length - 1,
                  pageIndex + 1,
                );
                setPageIndex(nextIndex);
                void persist({ pageIndex: nextIndex });
              }}
            >
              Próxima página
            </button>
          </footer>
        </section>

        <section className="student-hq-activity">
          <header>
            <h2>Atividade</h2>
            <span>
              {activityIndex + 1} de {manifest.activities.length}
            </span>
          </header>

          {activity ? (
            <>
              <h3>{activity.title}</h3>
              <p>{activity.instructions}</p>
              {activity.source_page_id ? (
                <button
                  type="button"
                  className="student-hq-source-link"
                  onClick={() => {
                    const index = storyPages.findIndex(
                      (item) => item.id === activity.source_page_id,
                    );
                    if (index >= 0) {
                      setPageIndex(index);
                      void persist({ pageIndex: index });
                    }
                  }}
                >
                  Voltar à página relacionada
                </button>
              ) : null}

              <ActivityResponseEditor
                activity={activity}
                answer={answers[activity.id]}
                onChange={(answer) =>
                  setAnswers((current) => ({
                    ...current,
                    [activity.id]: answer,
                  }))
                }
              />

              <div className="student-hq-activity-actions">
                <button
                  type="button"
                  disabled={activityIndex === 0}
                  onClick={() =>
                    setActivityIndex((value) => Math.max(0, value - 1))
                  }
                >
                  Atividade anterior
                </button>
                <button
                  type="button"
                  disabled={busy || !sessionIsActive}
                  onClick={() => void saveActivity()}
                >
                  {savedActivityIds.has(activity.id)
                    ? "Atualizar resposta"
                    : "Salvar resposta"}
                </button>
                <button
                  type="button"
                  disabled={
                    activityIndex >= manifest.activities.length - 1
                  }
                  onClick={() =>
                    setActivityIndex((value) =>
                      Math.min(
                        manifest.activities.length - 1,
                        value + 1,
                      ),
                    )
                  }
                >
                  Próxima atividade
                </button>
              </div>
            </>
          ) : (
            <p>Nenhuma atividade disponível.</p>
          )}
        </section>
      </div>

      <footer className="student-hq-footer">
        <span aria-live="polite">{error || message}</span>
        <button
          type="button"
          disabled={busy || !manifest.assessment.session}
          onClick={() => void persist()}
        >
          Salvar e continuar depois
        </button>
        <button
          type="button"
          disabled={
            busy ||
            !sessionIsActive ||
            answeredCount < manifest.activities.length
          }
          onClick={() => void submitAssessment()}
        >
          Enviar avaliação
        </button>
      </footer>
    </main>
  );
}
