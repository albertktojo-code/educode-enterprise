import { useEffect, useState } from "react";
import { adaptiveInsightsApi } from "../api";
import type { AdaptiveModelRecord } from "../types";
import "../styles.css";

export function AdaptiveModelsPage() {
  const [models, setModels] = useState<AdaptiveModelRecord[]>([]);
  const [error, setError] = useState("");
  async function load() {
    try { setModels(await adaptiveInsightsApi.listModels()); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Falha ao carregar"); }
  }
  useEffect(() => { void load(); }, []);
  return (
    <main className="ai-page">
      <h1>Modelos adaptativos versionados</h1>
      <p>Versões publicadas são imutáveis e identificadas por hash de configuração.</p>
      {error && <p role="alert">{error}</p>}
      <div className="ai-list">
        {models.map((model) => (
          <article className="ai-card" key={model.id}>
            <h2>{model.name} · {model.version}</h2>
            <p>{model.description}</p>
            <code>{model.configuration_hash}</code>
            <p>Status: {model.status}</p>
          </article>
        ))}
      </div>
    </main>
  );
}
