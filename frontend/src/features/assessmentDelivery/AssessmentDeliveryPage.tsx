import { useEffect, useState } from "react";

import { assessmentDeliveryApi } from "./api";
import type { AssessmentPublication, MonitoringSummary } from "./types";
import "./styles.css";

export function AssessmentDeliveryPage() {
  const [publications, setPublications] = useState<AssessmentPublication[]>([]);
  const [monitor, setMonitor] = useState<MonitoringSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    assessmentDeliveryApi
      .publications()
      .then(async (items) => {
        setPublications(items);
        if (items[0]) setMonitor(await assessmentDeliveryApi.monitor(items[0].id));
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Falha ao carregar."));
  }, []);

  return (
    <main className="assessment-delivery-page">
      <header>
        <p className="assessment-delivery-kicker">Sprint 15.2</p>
        <h1>Aplicacao de Avaliacoes</h1>
        <p>Publicacao, sessoes, salvamento automatico, acessibilidade e acompanhamento docente.</p>
      </header>

      {error ? <div className="assessment-delivery-error">{error}</div> : null}

      <section className="assessment-delivery-grid" aria-label="Indicadores da aplicacao">
        <article><strong>{publications.length}</strong><span>publicacoes</span></article>
        <article><strong>{monitor?.active_sessions ?? 0}</strong><span>sessoes ativas</span></article>
        <article><strong>{monitor?.submitted_sessions ?? 0}</strong><span>entregues</span></article>
        <article><strong>{monitor?.attention_sessions ?? 0}</strong><span>para acompanhamento</span></article>
      </section>

      <section className="assessment-delivery-panel">
        <h2>Publicacoes</h2>
        <table>
          <thead><tr><th>Codigo</th><th>Titulo</th><th>Janela</th><th>Duracao</th><th>Status</th></tr></thead>
          <tbody>
            {publications.map((publication) => (
              <tr key={publication.id}>
                <td>{publication.code}</td>
                <td>{publication.title}</td>
                <td>{new Date(publication.starts_at).toLocaleString()} - {new Date(publication.ends_at).toLocaleString()}</td>
                <td>{publication.duration_minutes} min</td>
                <td>{publication.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="assessment-delivery-notice">
        Eventos de integridade sao sinais descritivos para revisao humana. A Sprint 15.2 nao utiliza webcam, reconhecimento facial ou bloqueio invasivo do dispositivo.
      </section>
    </main>
  );
}
