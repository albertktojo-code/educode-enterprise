import { useState } from "react";
import { adaptiveInsightsApi } from "../api";
import "../styles.css";

const payload = {
  resource_type: "ACTIVITY",
  resource_id: "33333333-3333-3333-3333-333333333333",
  observations: Array.from({ length: 24 }, (_, index) => ({
    completed: index % 7 !== 0,
    score_before: 0.35 + (index % 3) * 0.05,
    score_after: 0.55 + (index % 4) * 0.06,
    correct: index % 4 !== 0,
    attempts: 1 + (index % 3),
    hints_used: index % 2,
    duration_seconds: 120 + index * 4,
  })),
};

export function MaterialEffectivenessPage() {
  const [result, setResult] = useState<unknown>();
  const [error, setError] = useState("");
  async function calculate() {
    try {
      setError("");
      setResult(await adaptiveInsightsApi.effectiveness(payload));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha no cálculo");
    }
  }
  return (
    <main className="ai-page">
      <h1>Eficácia descritiva dos materiais</h1>
      <p>Os indicadores não estabelecem causalidade e não alteram automaticamente materiais.</p>
      <button className="ai-button" onClick={calculate}>Calcular exemplo</button>
      {error && <p role="alert">{error}</p>}
      {result !== undefined && result !== null ? <pre>{JSON.stringify(result, null, 2)}</pre> : null}
    </main>
  );
}
