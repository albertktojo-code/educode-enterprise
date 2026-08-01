import { useEffect, useState } from "react";

import { instrumentGovernanceApi } from "./api";
import type { InstrumentDashboard, RomanGonzalezTemplate } from "./types";
import "./styles.css";

export function InstrumentGovernancePage() {
  const [dashboard, setDashboard] = useState<InstrumentDashboard | null>(null);
  const [template, setTemplate] = useState<RomanGonzalezTemplate | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      instrumentGovernanceApi.dashboard(),
      instrumentGovernanceApi.romanGonzalezTemplate(),
    ])
      .then(([summary, roman]) => {
        setDashboard(summary);
        setTemplate(roman);
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

  return (
    <main className="instrument-governance-page">
      <header>
        <p className="eyebrow">Sprint 15.3</p>
        <h1>Instrumentos externos e Pensamento Computacional</h1>
        <p>Licenciamento, protocolos, normas, importacoes autorizadas e interpretacao descritiva.</p>
      </header>

      {error && <div role="alert" className="error-card">{error}</div>}

      <section className="metric-grid" aria-label="Resumo institucional">
        {dashboard && Object.entries(dashboard).map(([key, value]) => (
          <article key={key} className="metric-card">
            <strong>{value}</strong>
            <span>{key.replaceAll("_", " ")}</span>
          </article>
        ))}
      </section>

      {template && (
        <section className="governance-card">
          <h2>{template.name}</h2>
          <p><strong>Suporte:</strong> {template.support_level}</p>
          <p>{template.notice}</p>
          <div className="status-row">
            <span>Licenca obrigatoria: {template.requires_license ? "sim" : "nao"}</span>
            <span>Itens protegidos incluidos: {template.protected_items_included ? "sim" : "nao"}</span>
          </div>
        </section>
      )}

      <section className="workflow-grid">
        {[
          ["1", "Licenca", "Registre a autorizacao e o escopo de uso."],
          ["2", "Protocolo", "Publique regras de aplicacao e acessibilidade."],
          ["3", "Normas", "Cadastre tabelas autorizadas por populacao."],
          ["4", "Importacao", "Valide checksum, manifesto e permissao."],
          ["5", "Resultados", "Interprete de forma descritiva e revisavel."],
        ].map(([step, title, text]) => (
          <article key={step} className="workflow-card">
            <span>{step}</span><h3>{title}</h3><p>{text}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
