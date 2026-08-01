import { useEffect, useState } from "react";

import { assessmentHubApi } from "./api";
import type { Blueprint, ExternalInstrument, QuestionItem } from "./types";
import "./styles.css";

export function AssessmentHubPage() {
  const [questions, setQuestions] = useState<QuestionItem[]>([]);
  const [blueprints, setBlueprints] = useState<Blueprint[]>([]);
  const [instruments, setInstruments] = useState<ExternalInstrument[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      assessmentHubApi.questions(),
      assessmentHubApi.blueprints(),
      assessmentHubApi.instruments(),
    ])
      .then(([questionData, blueprintData, instrumentData]) => {
        setQuestions(questionData);
        setBlueprints(blueprintData);
        setInstruments(instrumentData);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Falha ao carregar o modulo."));
  }, []);

  return (
    <main className="assessment-hub-page">
      <header>
        <p className="assessment-hub-kicker">Sprint 15</p>
        <h1>Avaliacoes Integradas</h1>
        <p>Questoes, instrumentos externos, tentativas, correcao e analytics no mesmo fluxo de evidencias.</p>
      </header>

      {error ? <div className="assessment-hub-error">{error}</div> : null}

      <section className="assessment-hub-grid" aria-label="Indicadores do modulo">
        <article><strong>{questions.length}</strong><span>questoes cadastradas</span></article>
        <article><strong>{blueprints.length}</strong><span>modelos de avaliacao</span></article>
        <article><strong>{instruments.length}</strong><span>instrumentos externos</span></article>
      </section>

      <section className="assessment-hub-panel">
        <h2>Banco unificado de questoes</h2>
        <table>
          <thead><tr><th>Codigo</th><th>Titulo</th><th>Disciplina</th><th>Versao</th><th>Status</th></tr></thead>
          <tbody>
            {questions.map((question) => (
              <tr key={question.id}>
                <td>{question.code}</td><td>{question.title}</td><td>{question.subject}</td>
                <td>{question.current_version}</td><td>{question.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="assessment-hub-notice">
        Instrumentos externos devem registrar autoria, fonte, licenca e permissao de uso. O modulo nao inclui itens protegidos de terceiros.
      </section>
    </main>
  );
}
