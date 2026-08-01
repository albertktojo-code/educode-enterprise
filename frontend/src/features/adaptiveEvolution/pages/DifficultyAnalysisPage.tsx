import { useState } from "react";
import { adaptiveEvolutionApi } from "../api";
import { ModuleCard } from "../components/ModuleCard";
import { NumberField } from "../components/NumberField";
import type { IndividualDifficultyResult, ObservedDifficultyResult } from "../types";
import "../styles.css";

export function DifficultyAnalysisPage() {
  const [mastery, setMastery] = useState(0.64);
  const [performance, setPerformance] = useState(0.7);
  const [individual, setIndividual] = useState<IndividualDifficultyResult | null>(null);
  const [predicted, setPredicted] = useState(0.5);
  const [attempts, setAttempts] = useState(40);
  const [correct, setCorrect] = useState(25);
  const [observed, setObserved] = useState<ObservedDifficultyResult | null>(null);
  const [error, setError] = useState("");

  async function calculateIndividual() {
    setError("");
    try {
      setIndividual(await adaptiveEvolutionApi.calculateIndividualDifficulty({
        mastery_score: mastery,
        confidence_score: 0.72,
        recent_performance: performance,
        average_hint_level: 1.2,
        prerequisite_mastery: 0.8,
        previous_difficulty_score: 0.48,
      }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha no cálculo individual.");
    }
  }

  async function calculateObserved() {
    setError("");
    try {
      setObserved(await adaptiveEvolutionApi.calculateObservedDifficulty({
        predicted_difficulty: predicted,
        attempts_count: attempts,
        correct_count: Math.min(correct, attempts),
        average_attempts: 1.7,
        average_hint_level: 1.4,
        abandonment_rate: 0.08,
        average_time_seconds: 150,
        expected_time_seconds: 120,
      }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha no cálculo observado.");
    }
  }

  return (
    <main className="ae-page">
      <h1>Dificuldade individual e observada</h1>
      {error && <p className="ae-error">{error}</p>}
      <div className="ae-grid ae-grid--two">
        <ModuleCard title="Dificuldade individual" description="Ajuste limitado a um nível por ciclo.">
          <NumberField label="Domínio" value={mastery} onChange={setMastery} />
          <NumberField label="Desempenho recente" value={performance} onChange={setPerformance} />
          <button className="ae-button" type="button" onClick={calculateIndividual}>Calcular</button>
          {individual && (
            <div className="ae-result-box">
              <strong>{individual.difficulty_level}</strong>
              <span>Score: {individual.difficulty_score.toFixed(2)}</span>
              <span>Ação: {individual.action}</span>
              <p>{individual.reason}</p>
            </div>
          )}
        </ModuleCard>

        <ModuleCard title="Prevista × observada" description="A dificuldade oficial não muda sem regra ou revisão.">
          <NumberField label="Dificuldade prevista" value={predicted} onChange={setPredicted} />
          <NumberField label="Tentativas" value={attempts} min={0} max={10000} step={1} onChange={setAttempts} />
          <NumberField label="Acertos" value={correct} min={0} max={10000} step={1} onChange={setCorrect} />
          <button className="ae-button" type="button" onClick={calculateObserved}>Comparar</button>
          {observed && (
            <div className="ae-result-box">
              <strong>{observed.classification}</strong>
              <span>Observada: {observed.observed_difficulty?.toFixed(2) ?? "sem evidência"}</span>
              <span>Diferença: {observed.difference?.toFixed(2) ?? "—"}</span>
              <span>Amostra: {observed.sample_size}</span>
            </div>
          )}
        </ModuleCard>
      </div>
    </main>
  );
}
