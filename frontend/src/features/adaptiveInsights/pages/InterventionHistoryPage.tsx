import { useState } from "react";
import { adaptiveInsightsApi } from "../api";
import "../styles.css";

const sample = {
  student_id: "11111111-1111-1111-1111-111111111111",
  learning_node_id: "22222222-2222-2222-2222-222222222222",
  current_mastery: 0.48,
  current_confidence: 0.68,
  candidate_interventions: ["REVISAO_GUIADA", "ATIVIDADE_VISUAL"],
  history: [
    {
      intervention_type: "REVISAO_GUIADA",
      mastery_before: 0.31,
      mastery_after: 0.47,
      completion_rate: 1,
      hint_level_average: 1.5,
      attempts_average: 1.8,
      days_ago: 5,
    },
  ],
};

export function InterventionHistoryPage() {
  const [text, setText] = useState(JSON.stringify(sample, null, 2));
  const [result, setResult] = useState<unknown>();
  const [error, setError] = useState("");
  async function run() {
    try {
      setError("");
      setResult(await adaptiveInsightsApi.recommend(JSON.parse(text)));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao recomendar");
    }
  }
  return (
    <main className="ai-page">
      <h1>Recomendação por histórico de intervenções</h1>
      <p>A saída é descritiva e sempre exige revisão docente.</p>
      <textarea value={text} onChange={(event) => setText(event.target.value)} rows={18} />
      <button className="ai-button" onClick={run}>Simular recomendação</button>
      {error && <p role="alert">{error}</p>}
      {result !== undefined && result !== null ? <pre>{JSON.stringify(result, null, 2)}</pre> : null}
    </main>
  );
}
