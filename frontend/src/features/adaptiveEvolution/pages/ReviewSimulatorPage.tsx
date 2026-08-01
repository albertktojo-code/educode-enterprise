import { useState } from "react";
import { adaptiveEvolutionApi } from "../api";
import { ModuleCard } from "../components/ModuleCard";
import { NumberField } from "../components/NumberField";
import type { SpacedReviewResult } from "../types";
import "../styles.css";

export function ReviewSimulatorPage() {
  const [mastery, setMastery] = useState(0.62);
  const [confidence, setConfidence] = useState(0.7);
  const [resultScore, setResultScore] = useState(0.75);
  const [hintLevel, setHintLevel] = useState(1);
  const [result, setResult] = useState<SpacedReviewResult | null>(null);
  const [error, setError] = useState("");

  async function calculate() {
    setError("");
    try {
      setResult(await adaptiveEvolutionApi.calculateReview({
        mastery_score: mastery,
        confidence_score: confidence,
        result_score: resultScore,
        hint_level_used: hintLevel,
      }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha ao calcular revisão.");
    }
  }

  return (
    <main className="ae-page">
      <h1>Simulador de revisão espaçada</h1>
      <ModuleCard title="Parâmetros" description="A simulação não altera a agenda real do estudante.">
        <div className="ae-form-grid">
          <NumberField label="Domínio" value={mastery} onChange={setMastery} />
          <NumberField label="Confiança" value={confidence} onChange={setConfidence} />
          <NumberField label="Resultado" value={resultScore} onChange={setResultScore} />
          <NumberField label="Maior pista usada" value={hintLevel} min={0} max={5} step={1} onChange={setHintLevel} />
        </div>
        <button className="ae-button" type="button" onClick={calculate}>Calcular próxima revisão</button>
        {error && <p className="ae-error">{error}</p>}
      </ModuleCard>

      {result && (
        <ModuleCard title="Resultado explicado" description={result.reason}>
          <div className="ae-metric-row">
            <strong>{result.interval_days} dias</strong>
            <span>Data: {result.scheduled_for}</span>
            <span>Prioridade: {result.priority}</span>
            <span>Regra: {result.rule_version}</span>
          </div>
        </ModuleCard>
      )}
    </main>
  );
}
