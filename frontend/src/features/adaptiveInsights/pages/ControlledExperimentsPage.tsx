import { useEffect, useState } from "react";
import { adaptiveInsightsApi } from "../api";
import type { ControlledExperimentRecord } from "../types";
import "../styles.css";

export function ControlledExperimentsPage() {
  const [experiments, setExperiments] = useState<ControlledExperimentRecord[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    adaptiveInsightsApi.listExperiments().then(setExperiments).catch((cause) => {
      setError(cause instanceof Error ? cause.message : "Falha ao carregar experimentos");
    });
  }, []);
  return (
    <main className="ai-page">
      <h1>Experimentos controlados</h1>
      <p>A comparação é descritiva e exige análise de amostra, equivalência e perdas.</p>
      {error && <p role="alert">{error}</p>}
      <div className="ai-list">
        {experiments.map((experiment) => (
          <article className="ai-card" key={experiment.id}>
            <h2>{experiment.name}</h2>
            <p>{experiment.hypothesis}</p>
            <p>Métrica: {experiment.primary_metric} · Status: {experiment.status}</p>
          </article>
        ))}
      </div>
    </main>
  );
}
