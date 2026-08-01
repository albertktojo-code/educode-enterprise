import { useEffect, useState } from "react";
import { assessmentAnalyticsApi } from "./api";
import "./styles.css";

export function AssessmentAnalyticsDashboard() {
  const [status, setStatus] = useState("carregando");
  const [runs, setRuns] = useState<unknown[]>([]);

  useEffect(() => {
    Promise.all([assessmentAnalyticsApi.health(), assessmentAnalyticsApi.runs()])
      .then(([health, data]) => { setStatus(`${health.status} - Sprint ${health.sprint}`); setRuns(data); })
      .catch((error: Error) => setStatus(error.message));
  }, []);

  return (
    <main className="analytics-page">
      <header>
        <p className="eyebrow">EduCode Enterprise</p>
        <h1>Analytics de Avaliações</h1>
        <p>Análise descritiva de itens, habilidades, turmas e instrumentos, com privacidade e explicabilidade.</p>
      </header>
      <section className="analytics-grid">
        <article><strong>Estado do módulo</strong><span>{status}</span></article>
        <article><strong>Execuções recentes</strong><span>{runs.length}</span></article>
        <article><strong>Privacidade</strong><span>Grupos pequenos suprimidos</span></article>
        <article><strong>Decisão pedagógica</strong><span>Revisão humana obrigatória</span></article>
      </section>
      <section className="analytics-panel">
        <h2>Indicadores disponíveis</h2>
        <ul>
          <li>Dificuldade prevista versus observada</li>
          <li>Índice de facilidade, discriminação, omissão e tempo</li>
          <li>Funcionamento dos distratores</li>
          <li>Cobertura e desempenho por BNCC e Pensamento Computacional</li>
          <li>Comparações institucionais com tamanho mínimo de grupo</li>
        </ul>
      </section>
    </main>
  );
}
