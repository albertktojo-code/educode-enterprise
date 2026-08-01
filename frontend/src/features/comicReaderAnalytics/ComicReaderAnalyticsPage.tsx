import { useEffect, useState } from "react";

import { comicReaderApi } from "../comicReaderAccess/api";
import type { ReaderRelease } from "../comicReaderAccess/types";
import { comicReaderAnalyticsApi } from "./api";
import type {
  AccessibilityMetric,
  ContentMetric,
  LearningMetric,
  ReaderAnalyticsOverview,
} from "./types";
import "./styles.css";

function isoDate(value: Date): string {
  return value.toISOString().slice(0, 10);
}

function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ComicReaderAnalyticsPage() {
  const today = new Date();
  const initialStart = new Date(today);
  initialStart.setDate(today.getDate() - 30);

  const [periodStart, setPeriodStart] = useState<string>(isoDate(initialStart));
  const [periodEnd, setPeriodEnd] = useState<string>(isoDate(today));
  const [releases, setReleases] = useState<ReaderRelease[]>([]);
  const [releaseId, setReleaseId] = useState<string>("");
  const [overview, setOverview] = useState<ReaderAnalyticsOverview | null>(null);
  const [content, setContent] = useState<ContentMetric[]>([]);
  const [learning, setLearning] = useState<LearningMetric[]>([]);
  const [accessibility, setAccessibility] = useState<AccessibilityMetric | null>(null);
  const [message, setMessage] = useState<string>("Carregando analytics...");
  const [busy, setBusy] = useState<boolean>(false);

  useEffect(() => {
    comicReaderApi.releases()
      .then((items) => {
        setReleases(items);
        setReleaseId(items[0]?.id ?? "");
      })
      .catch((error: Error) => setMessage(error.message));
  }, []);

  async function load(): Promise<void> {
    setBusy(true);
    try {
      const [overviewData, accessibilityData] = await Promise.all([
        comicReaderAnalyticsApi.overview(periodStart, periodEnd, releaseId || undefined),
        comicReaderAnalyticsApi.accessibility(periodStart, periodEnd, releaseId || undefined),
      ]);
      setOverview(overviewData);
      setAccessibility(accessibilityData);
      if (releaseId) {
        const [contentData, learningData] = await Promise.all([
          comicReaderAnalyticsApi.content(releaseId, periodStart, periodEnd),
          comicReaderAnalyticsApi.learning(releaseId, periodStart, periodEnd),
        ]);
        setContent(contentData);
        setLearning(learningData);
      } else {
        setContent([]);
        setLearning([]);
      }
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao carregar analytics.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
  }, [releaseId]);

  async function refresh(): Promise<void> {
    setBusy(true);
    try {
      const result = await comicReaderAnalyticsApi.refresh({
        period_start: periodStart,
        period_end: periodEnd,
        release_id: releaseId || undefined,
        generate_alerts: true,
      });
      setMessage(`Analytics atualizados. Job: ${String(result.job_id ?? "concluído")}`);
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao atualizar analytics.");
    } finally {
      setBusy(false);
    }
  }

  async function exportCsv(): Promise<void> {
    if (!releaseId) return;
    try {
      const blob = await comicReaderAnalyticsApi.exportCsv(
        releaseId,
        periodStart,
        periodEnd,
      );
      saveBlob(blob, `comic-reader-${releaseId}.csv`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao exportar CSV.");
    }
  }

  return (
    <section className="reader-analytics-page">
      <header className="page-header">
        <div>
          <span className="eyebrow">SPRINT 16.6</span>
          <h1>Analytics de leitura e aprendizagem</h1>
          <p>Engajamento, acessibilidade, conteúdo e relação com atividades.</p>
        </div>
      </header>

      <section className="panel analytics-filters">
        <label>
          Início
          <input
            type="date"
            value={periodStart}
            onChange={(event) => setPeriodStart(event.target.value)}
          />
        </label>
        <label>
          Fim
          <input
            type="date"
            value={periodEnd}
            onChange={(event) => setPeriodEnd(event.target.value)}
          />
        </label>
        <label>
          Release
          <select
            value={releaseId}
            onChange={(event) => setReleaseId(event.target.value)}
          >
            <option value="">Todos os releases</option>
            {releases.map((release) => (
              <option key={release.id} value={release.id}>
                {release.release_name}
              </option>
            ))}
          </select>
        </label>
        <button type="button" disabled={busy} onClick={() => void load()}>
          Aplicar
        </button>
        <button type="button" disabled={busy} onClick={() => void refresh()}>
          Atualizar métricas
        </button>
        <button
          type="button"
          disabled={!releaseId || busy}
          onClick={() => void exportCsv()}
        >
          Exportar CSV
        </button>
      </section>

      {message ? <div className="inline-message">{message}</div> : null}

      {overview !== null ? (
        <div className="analytics-card-grid">
          <article className="panel"><strong>{overview.students}</strong><span>estudantes</span></article>
          <article className="panel"><strong>{overview.sessions}</strong><span>sessões</span></article>
          <article className="panel"><strong>{Math.round(overview.active_seconds / 60)}</strong><span>minutos ativos</span></article>
          <article className="panel"><strong>{Math.round(overview.completion_rate * 100)}%</strong><span>conclusão</span></article>
          <article className="panel"><strong>{overview.glossary_opens}</strong><span>consultas ao glossário</span></article>
          <article className="panel"><strong>{Math.round(overview.narration_seconds / 60)}</strong><span>minutos narrados</span></article>
        </div>
      ) : null}

      {accessibility !== null ? (
        <section className="panel">
          <h2>Acessibilidade</h2>
          <p>
            Narração: {Math.round(accessibility.narration_adoption_rate * 100)}%
            {" · "}Recursos de acessibilidade:
            {" "}{Math.round(accessibility.accessibility_adoption_rate * 100)}%
          </p>
          <p>{accessibility.accessibility_actions} ajustes registrados.</p>
        </section>
      ) : null}

      <section className="panel">
        <h2>Páginas e quadros</h2>
        <div className="analytics-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Data</th><th>Página</th><th>Quadro</th><th>Visualizações</th>
                <th>Revisitas</th><th>Tempo</th><th>Glossário</th><th>Narração</th>
              </tr>
            </thead>
            <tbody>
              {content.map((item, index) => (
                <tr
                  key={`${item.metric_date}-${item.page_number ?? 0}-${item.panel_number ?? 0}-${index}`}
                >
                  <td>{item.metric_date}</td>
                  <td>{item.page_number ?? "—"}</td>
                  <td>{item.panel_number ?? "—"}</td>
                  <td>{item.view_count}</td>
                  <td>{item.revisit_count}</td>
                  <td>{item.total_active_seconds}s</td>
                  <td>{item.glossary_opens}</td>
                  <td>{item.narration_starts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <h2>Leitura e aprendizagem</h2>
        {learning.length ? (
          learning.map((item) => (
            <article
              className="learning-metric"
              key={`${item.scope_type}-${item.scope_id ?? "org"}-${item.assignment_id}`}
            >
              <strong>{item.scope_type} · amostra {item.sample_size}</strong>
              {item.privacy_suppressed ? (
                <p>Resultado suprimido pela regra de grupo mínimo.</p>
              ) : (
                <p>
                  Média: {item.average_score_percent.toFixed(1)}% · Correlação:
                  {" "}{item.reading_score_correlation?.toFixed(2) ?? "indisponível"}
                  {" · "}{item.interpretation}
                </p>
              )}
            </article>
          ))
        ) : (
          <p>Nenhuma atividade vinculada com dados suficientes.</p>
        )}
      </section>
    </section>
  );
}
