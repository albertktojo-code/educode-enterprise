import { useEffect, useMemo, useState } from "react";

import { assessmentReviewApi } from "./api";
import type { ReviewAssignment } from "./types";
import "./styles.css";

export function AssessmentReviewPage() {
  const [items, setItems] = useState<ReviewAssignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setItems(await assessmentReviewApi.listAssignments());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao carregar a fila.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const pending = useMemo(
    () => items.filter((item) => item.status !== "COMPLETED").length,
    [items],
  );

  async function start(id: string) {
    await assessmentReviewApi.startAssignment(id);
    await load();
  }

  return (
    <main className="assessment-review-page">
      <header>
        <p className="eyebrow">Sprint 15.4</p>
        <h1>Correção e revisão humana</h1>
        <p>
          Fila de respostas que exigem rubrica, análise docente, moderação ou
          recorreção. Nenhuma sugestão assistida conclui a nota sem decisão humana.
        </p>
      </header>

      <section className="review-metrics" aria-label="Resumo da fila">
        <article><strong>{items.length}</strong><span>Total</span></article>
        <article><strong>{pending}</strong><span>Pendentes</span></article>
        <article><strong>{items.length - pending}</strong><span>Concluídas</span></article>
      </section>

      {loading && <p role="status">Carregando fila de revisão…</p>}
      {error && <p role="alert" className="review-error">{error}</p>}

      {!loading && !error && (
        <section className="review-table-wrap">
          <table>
            <thead>
              <tr><th>Status</th><th>Resposta</th><th>Prioridade</th><th>Prazo</th><th>Ação</th></tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td><span className={`status status-${item.status.toLowerCase()}`}>{item.status}</span></td>
                  <td><code>{item.response_id}</code></td>
                  <td>{item.priority}</td>
                  <td>{item.due_at ? new Date(item.due_at).toLocaleString("pt-BR") : "Sem prazo"}</td>
                  <td>
                    {item.status === "PENDING" || item.status === "REOPENED" ? (
                      <button type="button" onClick={() => void start(item.id)}>Iniciar revisão</button>
                    ) : (
                      <span>—</span>
                    )}
                  </td>
                </tr>
              ))}
              {items.length === 0 && <tr><td colSpan={5}>Nenhuma revisão pendente.</td></tr>}
            </tbody>
          </table>
        </section>
      )}
    </main>
  );
}
