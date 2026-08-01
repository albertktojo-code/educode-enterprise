import { useEffect, useState } from "react";

import { assessmentReviewApi } from "./api";
import type { ReviewAppeal } from "./types";
import "./styles.css";

export function AppealManagementPage() {
  const [items, setItems] = useState<ReviewAppeal[]>([]);

  useEffect(() => {
    assessmentReviewApi.listAppeals().then(setItems).catch(() => setItems([]));
  }, []);

  return (
    <main className="assessment-review-page">
      <header>
        <p className="eyebrow">Direito de revisão</p>
        <h1>Contestações e recorreções</h1>
        <p>Decisões preservam a nota anterior, a justificativa e a trilha de auditoria.</p>
      </header>
      <section className="review-cards">
        {items.map((item) => (
          <article key={item.id}>
            <div><strong>{item.reason_code}</strong><span>{item.status}</span></div>
            <p>{item.statement}</p>
            <small>Tentativa: {item.attempt_id}</small>
          </article>
        ))}
        {items.length === 0 && <p>Nenhuma contestação registrada.</p>}
      </section>
    </main>
  );
}
