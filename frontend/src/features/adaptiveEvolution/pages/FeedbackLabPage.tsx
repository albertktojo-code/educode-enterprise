import { useState } from "react";
import { adaptiveEvolutionApi } from "../api";
import { ModuleCard } from "../components/ModuleCard";
import type { FeedbackResult } from "../types";
import "../styles.css";

export function FeedbackLabPage() {
  const [skill, setSkill] = useState("Decomposição de problemas");
  const [errorType, setErrorType] = useState("DECOMPOSITION");
  const [mastery, setMastery] = useState("EM_DESENVOLVIMENTO");
  const [result, setResult] = useState<FeedbackResult | null>(null);
  const [error, setError] = useState("");

  async function preview() {
    setError("");
    try {
      setResult(await adaptiveEvolutionApi.adaptFeedback({
        is_correct: false,
        mastery_level: mastery,
        error_type: errorType,
        attempt_number: 2,
        hint_level_used: 1,
        skill_name: skill,
      }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha ao adaptar feedback.");
    }
  }

  return (
    <main className="ae-page">
      <h1>Laboratório de feedback adaptado</h1>
      <ModuleCard title="Contexto pedagógico" description="Prévia determinística; não substitui a revisão docente.">
        <div className="ae-form-grid">
          <label className="ae-field"><span>Habilidade</span><input value={skill} onChange={(event) => setSkill(event.target.value)} /></label>
          <label className="ae-field"><span>Nível de domínio</span><select value={mastery} onChange={(event) => setMastery(event.target.value)}><option>INICIAL</option><option>EM_DESENVOLVIMENTO</option><option>ADEQUADO</option><option>AVANÇADO</option><option>DOMINADO</option></select></label>
          <label className="ae-field"><span>Tipo de erro</span><select value={errorType} onChange={(event) => setErrorType(event.target.value)}><option value="CONCEPTUAL">Conceitual</option><option value="INTERPRETATION">Interpretação</option><option value="DECOMPOSITION">Decomposição</option><option value="ABSTRACTION">Abstração</option><option value="ALGORITHMIC">Algorítmico</option><option value="DEBUGGING">Depuração</option></select></label>
        </div>
        <button className="ae-button" type="button" onClick={preview}>Gerar prévia</button>
        {error && <p className="ae-error">{error}</p>}
      </ModuleCard>
      {result && <ModuleCard title={result.feedback_type} description={result.explanation}><blockquote className="ae-feedback">{result.content}</blockquote><p>Próxima ação: <strong>{result.next_action}</strong></p></ModuleCard>}
    </main>
  );
}
