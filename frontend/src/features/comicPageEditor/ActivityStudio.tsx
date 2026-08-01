import { useEffect, useMemo, useState } from "react";

import { comicPageEditorApi } from "./api";
import type { ComicPage, HQActivity } from "./types";

interface Props {
  open: boolean;
  projectId: string;
  pages: ComicPage[];
  selectedPageId?: string;
  selectedPanelId?: string;
  onClose: () => void;
  onCreated: () => void;
}

const DEFAULT_TYPES = [
  ["MULTIPLE_CHOICE", "Múltipla escolha"],
  ["TRUE_FALSE", "Verdadeiro ou falso"],
  ["MATCHING", "Associação"],
  ["ORDERING", "Ordenação"],
  ["FILL_BLANKS", "Completar lacunas"],
  ["CROSSWORD", "Palavras cruzadas"],
  ["WORD_SEARCH", "Caça-palavras"],
  ["SHORT_ANSWER", "Resposta curta"],
  ["ESSAY", "Discursiva"],
  ["COMPUTATIONAL_THINKING", "Pensamento Computacional"],
  ["MATHEMATICS", "Matemática"],
] as const;

export function ActivityStudio({
  open,
  projectId,
  pages,
  selectedPageId,
  selectedPanelId,
  onClose,
  onCreated,
}: Props) {
  const [activities, setActivities] = useState<HQActivity[]>([]);
  const [type, setType] = useState("MULTIPLE_CHOICE");
  const [title, setTitle] = useState("Atividade pós-HQ");
  const [instructions, setInstructions] = useState(
    "Responda com base na história.",
  );
  const [subject, setSubject] = useState("Pensamento Computacional");
  const [theme, setTheme] = useState("");
  const [schoolYear, setSchoolYear] = useState("6º ano");
  const [difficulty, setDifficulty] = useState("BASIC");
  const [bncc, setBncc] = useState("");
  const [pillars, setPillars] = useState("DECOMPOSITION,ALGORITHMS");
  const [optionsText, setOptionsText] = useState(
    `Decomposição|true
Memorização|false
Repetição|false`,
  );
  const [wordsText, setWordsText] = useState(
    `ALGORITMO
PADRÃO
ABSTRAÇÃO`,
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const sourcePage = useMemo(
    () => pages.find((page) => page.id === selectedPageId),
    [pages, selectedPageId],
  );

  useEffect(() => {
    if (open) void load();
  }, [open, projectId]);

  async function load(): Promise<void> {
    try {
      setActivities(await comicPageEditorApi.listActivities(projectId));
    } catch {
      setActivities([]);
    }
  }

  function activityPayload(): Record<string, unknown> {
    if (type === "MULTIPLE_CHOICE") {
      return {
        options: optionsText
          .split("\n")
          .map((line, index) => {
            const [text, correct] = line.split("|");
            return {
              id: String.fromCharCode(65 + index),
              text: text?.trim(),
              correct: correct?.trim() === "true",
            };
          })
          .filter((item) => item.text),
      };
    }
    if (type === "TRUE_FALSE") {
      return { correct: true };
    }
    if (type === "WORD_SEARCH") {
      return {
        words: wordsText
          .split("\n")
          .map((item) => item.trim())
          .filter(Boolean),
      };
    }
    if (type === "CROSSWORD") {
      return {
        entries: wordsText
          .split("\n")
          .map((item, index) => ({
            answer: item.trim(),
            clue: `Pista ${index + 1} relacionada à HQ`,
          }))
          .filter((item) => item.answer),
      };
    }
    if (type === "ORDERING") {
      return {
        items: instructions
          .split(";")
          .map((item) => item.trim())
          .filter(Boolean),
      };
    }
    if (type === "MATCHING") {
      return {
        pairs: optionsText
          .split("\n")
          .map((line) => {
            const [left, right] = line.split("|");
            return { left, right };
          })
          .filter((item) => item.left && item.right),
      };
    }
    if (type === "FILL_BLANKS") {
      return {
        blanks: wordsText
          .split("\n")
          .map((line) => line.trim())
          .filter(Boolean)
          .map((line, index) => ({
            id: String(index),
            label: line.split("|")[0]?.trim() || `Lacuna ${index + 1}`,
          }))
      };
    }
    return { prompt: instructions };
  }

  function answerKey(payload: Record<string, unknown>): Record<string, unknown> {
    if (type === "MULTIPLE_CHOICE") {
      const options = payload.options as Array<{
        id: string;
        correct: boolean;
      }>;
      return {
        correct_option_ids: options
          .filter((item) => item.correct)
          .map((item) => item.id),
      };
    }
    if (type === "TRUE_FALSE") return { correct: true };
    if (type === "MATCHING") return { pairs: payload.pairs };
    if (type === "ORDERING") return { items: payload.items };
    if (type === "FILL_BLANKS") {
      return {
        answers: wordsText
          .split("\n")
          .map((line) => line.split("|")[1]?.trim() || "")
          .filter(Boolean),
      };
    }
    if (type === "WORD_SEARCH") return { words: payload.words };
    if (type === "CROSSWORD") return { entries: payload.entries };
    if (type === "SHORT_ANSWER") {
      return {
        accepted_answers: wordsText
          .split("\n")
          .map((item) => item.trim())
          .filter(Boolean),
      };
    }
    return {};
  }

  async function create(): Promise<void> {
    setBusy(true);
    setMessage("");
    try {
      const payload = activityPayload();
      if (type === "WORD_SEARCH") {
        const words = payload.words as string[];
        const generated = await comicPageEditorApi.buildWordSearch(words, 12);
        Object.assign(payload, generated);
      }
      if (type === "CROSSWORD") {
        const validation = await comicPageEditorApi.validateCrossword(
          payload.entries as Array<{ answer: string; clue: string }>,
        );
        if (!validation.valid) {
          setMessage(validation.errors.join(" "));
          return;
        }
        Object.assign(payload, validation);
      }
      await comicPageEditorApi.createActivity(projectId, {
        activity_type: type,
        title,
        instructions,
        subject,
        theme,
        school_year: schoolYear,
        difficulty,
        layout_code:
          type === "CROSSWORD"
            ? "ACTIVITY_CROSSWORD"
            : type === "WORD_SEARCH"
              ? "ACTIVITY_WORD_SEARCH"
              : "ACTIVITY_FULL",
        activity_payload: payload,
        answer_key: answerKey(payload),
        explanation: "Revise a página da HQ relacionada à questão.",
        rubric: {},
        accessibility: {
          keyboard_navigation: true,
          text_alternative: true,
          high_contrast_ready: true,
        },
        bncc_codes: bncc
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        ct_pillars: pillars
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        source_page_id: sourcePage?.pageType === "STORY"
          ? sourcePage.id
          : null,
        source_panel_id: selectedPanelId || null,
        display_order: activities.length + 1,
        max_score: 1,
        predicted_difficulty: 0.5,
      });
      await comicPageEditorApi.ensureAnswerKeyPage(projectId);
      await load();
      onCreated();
      setMessage("Atividade criada como rascunho e vinculada ao Assessment Hub.");
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Falha ao criar atividade.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function approve(activityId: string): Promise<void> {
    setBusy(true);
    try {
      await comicPageEditorApi.approveActivity(activityId);
      await load();
    } finally {
      setBusy(false);
    }
  }

  if (!open) return null;

  return (
    <div className="activity-studio-overlay" role="dialog" aria-modal="true">
      <section className="activity-studio-dialog">
        <header>
          <div>
            <span className="hq-eyebrow">Sprint 16.11</span>
            <h2>Atividades interativas pós-HQ</h2>
          </div>
          <button type="button" onClick={onClose}>Fechar</button>
        </header>

        <div className="activity-studio-grid">
          <section className="activity-form">
            <label>
              Tipo
              <select value={type} onChange={(e) => setType(e.target.value)}>
                {DEFAULT_TYPES.map(([code, label]) => (
                  <option key={code} value={code}>{label}</option>
                ))}
              </select>
            </label>
            <label>
              Título
              <input value={title} onChange={(e) => setTitle(e.target.value)} />
            </label>
            <label>
              Instruções
              <textarea value={instructions} onChange={(e) => setInstructions(e.target.value)} />
            </label>
            <div className="activity-form-row">
              <label>
                Disciplina
                <input value={subject} onChange={(e) => setSubject(e.target.value)} />
              </label>
              <label>
                Tema
                <input value={theme} onChange={(e) => setTheme(e.target.value)} />
              </label>
            </div>
            <div className="activity-form-row">
              <label>
                Ano
                <input value={schoolYear} onChange={(e) => setSchoolYear(e.target.value)} />
              </label>
              <label>
                Dificuldade
                <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
                  <option value="INTRODUCTORY">Introdutório</option>
                  <option value="BASIC">Básico</option>
                  <option value="INTERMEDIATE">Intermediário</option>
                  <option value="ADVANCED">Avançado</option>
                  <option value="CHALLENGE">Desafio</option>
                </select>
              </label>
            </div>
            <label>
              BNCC, separada por vírgulas
              <input value={bncc} onChange={(e) => setBncc(e.target.value)} />
            </label>
            <label>
              Pilares de PC
              <input value={pillars} onChange={(e) => setPillars(e.target.value)} />
            </label>

            {["MULTIPLE_CHOICE", "MATCHING"].includes(type) ? (
              <label>
                Itens: texto|true ou esquerda|direita
                <textarea value={optionsText} onChange={(e) => setOptionsText(e.target.value)} />
              </label>
            ) : null}

            {[
              "CROSSWORD",
              "WORD_SEARCH",
              "FILL_BLANKS",
              "SHORT_ANSWER",
            ].includes(type) ? (
              <label>
                {type === "FILL_BLANKS"
                  ? "Lacunas: rótulo|resposta, uma por linha"
                  : type === "SHORT_ANSWER"
                    ? "Respostas aceitas, uma por linha"
                    : "Palavras, uma por linha"}
                <textarea value={wordsText} onChange={(e) => setWordsText(e.target.value)} />
              </label>
            ) : null}

            <button type="button" disabled={busy} onClick={() => void create()}>
              Criar atividade e página
            </button>
            {message ? <p className="activity-message">{message}</p> : null}
          </section>

          <section className="activity-list">
            <h3>Atividades vinculadas</h3>
            {activities.map((item) => (
              <article key={item.id}>
                <header>
                  <b>{item.title}</b>
                  <span>{item.status}</span>
                </header>
                <p>{item.activityType} · {item.difficulty}</p>
                <small>
                  Página relacionada: {
                    String(item.pedagogicalLinks.source_page_id ?? "não definida")
                  }
                </small>
                {item.status === "DRAFT" ? (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void approve(item.id)}
                  >
                    Revisar e aprovar
                  </button>
                ) : null}
              </article>
            ))}
          </section>
        </div>
      </section>
    </div>
  );
}
