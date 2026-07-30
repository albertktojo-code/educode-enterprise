import { useState } from "react";
import { adaptiveInsightsApi } from "../api";
import "../styles.css";

const sample = {
  paths: [
    {
      path_id: "44444444-4444-4444-4444-444444444444",
      path_name: "Pensamento Computacional — 6º ano",
      assigned_students: 90,
      active_students: 75,
      completed_students: 28,
      average_progress: 0.56,
      overdue_reviews: 18,
      interventions_count: 42,
      average_mastery: 0.61,
    },
  ],
};

export function InstitutionalPathsPage() {
  const [result, setResult] = useState<unknown>();
  return (
    <main className="ai-page">
      <h1>Painel institucional de trilhas</h1>
      <button className="ai-button" onClick={async () => setResult(await adaptiveInsightsApi.dashboard(sample))}>
        Carregar consolidação demonstrativa
      </button>
      {result !== undefined && result !== null ? <pre>{JSON.stringify(result, null, 2)}</pre> : null}
    </main>
  );
}
