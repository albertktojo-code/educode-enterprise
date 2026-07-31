import { useState } from "react";

import { comicPageEditorApi } from "./api";
import type { HQLearningAnalyticsSnapshot } from "./types";

interface Props {
  open: boolean;
  deliveryId: string;
  onClose: () => void;
}

export function LearningAnalyticsPanel({
  open,
  deliveryId,
  onClose,
}: Props) {
  const [data, setData] = useState<HQLearningAnalyticsSnapshot | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function load(): Promise<void> {
    if (!deliveryId) return;
    setBusy(true);
    try {
      setData(
        await comicPageEditorApi.latestLearningAnalytics(deliveryId),
      );
    } finally {
      setBusy(false);
    }
  }

  async function generate(): Promise<void> {
    if (!deliveryId) return;
    setBusy(true);
    setMessage("");
    try {
      const result =
        await comicPageEditorApi.generateLearningAnalytics(
          deliveryId,
          { scope_type: "PUBLICATION" },
        );
      setData(result);
      setMessage("Analytics atualizados.");
    } finally {
      setBusy(false);
    }
  }

  if (!open) return null;

  const metrics = data?.metrics ?? {};

  return (
    <div className="learning-analytics-overlay" role="dialog" aria-modal="true">
      <section className="learning-analytics-dialog">
        <header>
          <div>
            <span className="hq-eyebrow">Sprint 16.11.5</span>
            <h2>Analytics pós-HQ</h2>
          </div>
          <button type="button" onClick={onClose}>Fechar</button>
        </header>

        {!deliveryId ? (
          <p>Crie uma aplicação para gerar os indicadores.</p>
        ) : null}

        <div className="hq-analytics-actions">
          <button
            type="button"
            disabled={busy || !deliveryId}
            onClick={() => void load()}
          >
            Carregar último
          </button>
          <button
            type="button"
            disabled={busy || !deliveryId}
            onClick={() => void generate()}
          >
            Gerar agora
          </button>
        </div>

        {message ? <p>{message}</p> : null}

        <div className="analytics-kpis">
          <article>
            <b>Conclusão</b>
            <strong>{metrics.completion_rate ?? 0}%</strong>
          </article>
          <article>
            <b>Leitura completa</b>
            <strong>{metrics.reading_completion_rate ?? 0}%</strong>
          </article>
          <article>
            <b>Atividades completas</b>
            <strong>{metrics.activity_completion_rate ?? 0}%</strong>
          </article>
          <article>
            <b>Retomada</b>
            <strong>{metrics.resume_usage_rate ?? 0}%</strong>
          </article>
        </div>

        <div className="analytics-sections">
          <section>
            <h3>Habilidades</h3>
            {(data?.skill_metrics ?? []).map((item) => (
              <article key={`${item.skill_type}-${item.skill_code}`}>
                <b>{item.skill_code}</b>
                <span>{item.accuracy}% de acerto</span>
              </article>
            ))}
          </section>

          <section>
            <h3>Atividades</h3>
            {(data?.activity_metrics ?? []).map((item) => (
              <article key={item.activity_id}>
                <b>{item.title}</b>
                <span>
                  {item.accuracy}% · {item.attempt_count} tentativas
                </span>
              </article>
            ))}
          </section>

          <section>
            <h3>Páginas</h3>
            {(data?.page_metrics ?? []).map((item) => (
              <article key={item.page_id}>
                <b>Página {item.page_number}</b>
                <span>{item.revisit_count} releituras</span>
              </article>
            ))}
          </section>

          <section>
            <h3>Alertas</h3>
            {(data?.alerts ?? []).map((item, index) => (
              <article
                key={`${item.code}-${index}`}
                className={`alert-${String(item.severity).toLowerCase()}`}
              >
                <b>{item.code}</b>
                <span>{item.message}</span>
              </article>
            ))}
          </section>
        </div>

        <section className="analytics-correlation">
          <h3>Relação entre releitura e acerto</h3>
          <pre>{JSON.stringify(data?.correlations ?? [], null, 2)}</pre>
        </section>
      </section>
    </div>
  );
}
