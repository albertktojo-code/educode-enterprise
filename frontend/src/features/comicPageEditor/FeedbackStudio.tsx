import { useEffect, useMemo, useState } from "react";

import { comicPageEditorApi } from "./api";
import type { HQActivity } from "./types";

interface Props {
  open: boolean;
  projectId: string;
  onClose: () => void;
}

export function FeedbackStudio({
  open,
  projectId,
  onClose,
}: Props) {
  const [activities, setActivities] = useState<HQActivity[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [mode, setMode] = useState("AUTOMATIC");
  const [correctText, setCorrectText] = useState(
    "Muito bem! Você compreendeu o conceito.",
  );
  const [incorrectText, setIncorrectText] = useState(
    "Revise a página indicada da HQ e tente novamente.",
  );
  const [hintText, setHintText] = useState(
    "Observe como o personagem dividiu o problema em etapas.",
  );
  const [criterionName, setCriterionName] = useState("Compreensão");
  const [criterionScore, setCriterionScore] = useState(1);
  const [appealEnabled, setAppealEnabled] = useState(true);
  const [simulation, setSimulation] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const selected = useMemo(
    () => activities.find((item) => item.id === selectedId),
    [activities, selectedId],
  );

  useEffect(() => {
    if (open) void load();
  }, [open, projectId]);

  async function load(): Promise<void> {
    const loaded = await comicPageEditorApi.listActivities(projectId);
    setActivities(loaded);
    setSelectedId((current) => current || loaded[0]?.id || "");
  }

  async function save(): Promise<void> {
    if (!selected) return;
    setBusy(true);
    setMessage("");
    try {
      await comicPageEditorApi.saveActivityFeedbackProfile(selected.id, {
        correction_mode: mode,
        feedback_templates: {
          correct: correctText,
          incorrect: incorrectText,
          requires_review:
            "Sua resposta será analisada pelo professor.",
        },
        graduated_hints: [
          {
            level: 1,
            text: hintText,
            source_reference:
              selected.pedagogicalLinks,
          },
        ],
        common_errors: [],
        review_rules: {
          teacher_final_decision: true,
          preserve_previous_score_on_regrade: true,
        },
        appeal_enabled: appealEnabled,
        rubric:
          mode === "AUTOMATIC"
            ? null
            : {
                name: `Rubrica — ${selected.title}`,
                description:
                  "Rubrica vinculada à atividade pós-HQ.",
                maximum_score: criterionScore,
                criteria: [
                  {
                    code: "COMPREHENSION",
                    name: criterionName,
                    description:
                      "Avalia a compreensão do conteúdo apresentado.",
                    criterion_type: "SCALE",
                    maximum_score: criterionScore,
                    levels: [],
                    skill_mappings: [],
                  },
                ],
                score_rules: {},
                skill_mappings: [],
                accessibility: {},
              },
      });
      setMessage("Perfil de correção salvo para revisão.");
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Falha ao salvar.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function approve(): Promise<void> {
    if (!selected) return;
    setBusy(true);
    try {
      await comicPageEditorApi.approveActivityFeedbackProfile(
        selected.id,
      );
      setMessage("Perfil e rubrica aprovados.");
    } finally {
      setBusy(false);
    }
  }

  async function simulate(): Promise<void> {
    if (!selected) return;
    setBusy(true);
    try {
      const response =
        selected.activityType === "TRUE_FALSE"
          ? { answer: true }
          : selected.activityType === "MULTIPLE_CHOICE"
            ? { selected_option_ids: ["A"] }
            : {};
      const result =
        await comicPageEditorApi.simulateActivityCorrection(
          selected.id,
          response,
        );
      setSimulation(JSON.stringify(result, null, 2));
    } finally {
      setBusy(false);
    }
  }

  if (!open) return null;

  return (
    <div className="feedback-studio-overlay" role="dialog" aria-modal="true">
      <section className="feedback-studio-dialog">
        <header>
          <div>
            <span className="hq-eyebrow">Sprint 16.11.1</span>
            <h2>Correção, rubricas e feedback</h2>
          </div>
          <button type="button" onClick={onClose}>Fechar</button>
        </header>

        <div className="feedback-studio-grid">
          <section>
            <label>
              Atividade
              <select
                value={selectedId}
                onChange={(event) => setSelectedId(event.target.value)}
              >
                {activities.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.title}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Modo de correção
              <select
                value={mode}
                onChange={(event) => setMode(event.target.value)}
              >
                <option value="AUTOMATIC">Automática</option>
                <option value="RUBRIC">Rubrica</option>
                <option value="ASSISTED">Assistida por IA</option>
                <option value="HUMAN">Humana</option>
              </select>
            </label>

            <label>
              Feedback para acerto
              <textarea
                value={correctText}
                onChange={(event) => setCorrectText(event.target.value)}
              />
            </label>

            <label>
              Feedback para erro
              <textarea
                value={incorrectText}
                onChange={(event) => setIncorrectText(event.target.value)}
              />
            </label>

            <label>
              Primeira dica gradual
              <textarea
                value={hintText}
                onChange={(event) => setHintText(event.target.value)}
              />
            </label>

            {mode !== "AUTOMATIC" ? (
              <div className="feedback-rubric-row">
                <label>
                  Critério
                  <input
                    value={criterionName}
                    onChange={(event) =>
                      setCriterionName(event.target.value)
                    }
                  />
                </label>
                <label>
                  Pontuação máxima
                  <input
                    type="number"
                    min={0.1}
                    step={0.1}
                    value={criterionScore}
                    onChange={(event) =>
                      setCriterionScore(Number(event.target.value))
                    }
                  />
                </label>
              </div>
            ) : null}

            <label className="feedback-check">
              <input
                type="checkbox"
                checked={appealEnabled}
                onChange={(event) =>
                  setAppealEnabled(event.target.checked)
                }
              />
              Permitir contestação e recorreção
            </label>

            <div className="feedback-actions">
              <button type="button" disabled={busy} onClick={() => void save()}>
                Salvar perfil
              </button>
              <button type="button" disabled={busy} onClick={() => void approve()}>
                Aprovar
              </button>
              <button type="button" disabled={busy} onClick={() => void simulate()}>
                Simular correção
              </button>
            </div>
            {message ? <p>{message}</p> : null}
          </section>

          <section>
            <h3>Prévia da devolutiva</h3>
            <article>
              <b>Resposta correta</b>
              <p>{correctText}</p>
            </article>
            <article>
              <b>Resposta incorreta</b>
              <p>{incorrectText}</p>
              <small>{hintText}</small>
            </article>
            <pre>{simulation || "Execute uma simulação."}</pre>
          </section>
        </div>
      </section>
    </div>
  );
}
