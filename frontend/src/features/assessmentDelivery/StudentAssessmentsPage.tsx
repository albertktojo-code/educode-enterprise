import { useState } from "react";

import { assessmentDeliveryApi } from "./api";
import type { AvailableAssessment } from "./types";
import "./styles.css";

export function StudentAssessmentsPage() {
  const [studentId, setStudentId] = useState("");
  const [items, setItems] = useState<AvailableAssessment[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      setItems(await assessmentDeliveryApi.available(studentId));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Falha ao consultar avaliacoes.");
    }
  }

  return (
    <main className="assessment-delivery-page">
      <header><p className="assessment-delivery-kicker">Area do estudante</p><h1>Minhas avaliacoes</h1></header>
      <section className="assessment-delivery-panel assessment-delivery-search">
        <label htmlFor="student-id">Identificador do estudante</label>
        <input id="student-id" value={studentId} onChange={(event) => setStudentId(event.target.value)} />
        <button type="button" onClick={load} disabled={!studentId}>Consultar</button>
      </section>
      {error ? <div className="assessment-delivery-error">{error}</div> : null}
      <section className="assessment-delivery-grid">
        {items.map((item) => (
          <article key={item.publication.id}>
            <strong>{item.publication.title}</strong>
            <span>{item.effective_status} · {item.attempts_used}/{item.attempts_allowed} tentativas</span>
            <button type="button" disabled={!item.can_start}>Iniciar</button>
          </article>
        ))}
      </section>
    </main>
  );
}
