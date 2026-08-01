import { useEffect, useState } from "react";

import { interventionOrchestrationApi } from "./api";
import type { StudentIntervention } from "./types";
import "./styles.css";

function actionTitle(action: Record<string, unknown>): string {
  return typeof action.title === "string" ? action.title : "Ação pedagógica";
}

export function StudentInterventionsPage() {
  const [items, setItems] = useState<StudentIntervention[]>([]);
  const [message, setMessage] = useState<string>("Carregando intervenções...");

  useEffect(() => {
    interventionOrchestrationApi
      .myInterventions()
      .then((data) => {
        setItems(data);
        setMessage(data.length ? "" : "Nenhuma intervenção atribuída.");
      })
      .catch((error: Error) => setMessage(error.message));
  }, []);

  async function acknowledge(item: StudentIntervention): Promise<void> {
    try {
      await interventionOrchestrationApi.acknowledge(item.id);
      setMessage("Intervenção confirmada.");
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Falha ao confirmar.",
      );
    }
  }

  return (
    <section className="intervention-orchestration-page">
      <header className="page-header">
        <div>
          <span className="eyebrow">MINHAS INTERVENÇÕES</span>
          <h1>Plano de apoio pedagógico</h1>
          <p>
            Atividades e recursos definidos pelo professor a partir das
            evidências de aprendizagem.
          </p>
        </div>
      </header>

      {message ? <div className="inline-message">{message}</div> : null}

      <div className="intervention-card-list">
        {items.map((item) => (
          <article className="panel student-intervention-card" key={item.id}>
            <span>
              {item.intervention_type} · {item.status} ·{" "}
              {item.scope === "classroom" ? "turma" : "individual"}
            </span>
            <h2>{item.expected_outcome}</h2>
            <p>{item.student_message}</p>
            <ol>
              {item.actions.map((action, index) => (
                <li key={`${item.id}-${index}`}>{actionTitle(action)}</li>
              ))}
            </ol>
            {item.status !== "completed" ? (
              <button type="button" onClick={() => void acknowledge(item)}>
                Confirmar recebimento
              </button>
            ) : (
              <p><strong>Resultado:</strong> {item.result_summary}</p>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
