import { useState } from "react";
import { adaptiveInsightsApi } from "../api";
import "../styles.css";

const payload = {
  model_configuration: { advance_mastery: 0.75, minimum_confidence: 0.55, minimum_evidences: 3 },
  profiles: [
    {
      student_id: "55555555-5555-5555-5555-555555555555",
      learning_node_id: "66666666-6666-6666-6666-666666666666",
      mastery_score: 0.78,
      confidence_score: 0.72,
      evidences_count: 5,
      intervention_failures: 0,
      overdue_reviews: 0,
    },
  ],
};

export function RecommendationSimulationPage() {
  const [result, setResult] = useState<unknown>();
  return (
    <main className="ai-page">
      <h1>Simulação de recomendações</h1>
      <p>A simulação não altera trilhas, notas, domínio nem agenda.</p>
      <button className="ai-button" onClick={async () => setResult(await adaptiveInsightsApi.simulate(payload))}>
        Executar simulação
      </button>
      {result !== undefined && result !== null ? <pre>{JSON.stringify(result, null, 2)}</pre> : null}
    </main>
  );
}
