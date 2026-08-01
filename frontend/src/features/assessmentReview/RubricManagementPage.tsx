import { useEffect, useState } from "react";

import { assessmentReviewApi } from "./api";
import type { ReviewRubric } from "./types";
import "./styles.css";

export function RubricManagementPage() {
  const [items, setItems] = useState<ReviewRubric[]>([]);

  useEffect(() => {
    assessmentReviewApi.listRubrics().then(setItems).catch(() => setItems([]));
  }, []);

  return (
    <main className="assessment-review-page">
      <header><p className="eyebrow">Governança</p><h1>Rubricas versionadas</h1></header>
      <section className="review-cards">
        {items.map((item) => (
          <article key={item.id}>
            <div><strong>{item.code}</strong><span>{item.status}</span></div>
            <h2>{item.name}</h2>
            <p>{item.description}</p>
            <small>Versão atual: {item.current_version}</small>
          </article>
        ))}
        {items.length === 0 && <p>Nenhuma rubrica cadastrada.</p>}
      </section>
    </main>
  );
}
