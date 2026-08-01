import { useEffect, useMemo, useState, type ChangeEvent } from "react";

import { interventionEffectivenessApi } from "./api";
import type {
  EffectivenessDashboard,
  EffectivenessMetric,
  EffectivenessWindow,
  EvaluationCheckpoint,
} from "./types";
import "./styles.css";

function isoDate(value: Date): string {
  return value.toISOString().slice(0, 10);
}

function defaultPeriod(): { start: string; end: string } {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 90);
  return { start: isoDate(start), end: isoDate(end) };
}

function percentage(value?: number | null): string {
  return value === null || value === undefined
    ? "—"
    : `${(value * 100).toFixed(1)}%`;
}

function signedPercentage(value?: number | null): string {
  if (value === null || value === undefined) return "—";
  const percent = value * 100;
  return `${percent >= 0 ? "+" : ""}${percent.toFixed(1)} p.p.`;
}

function formatDate(value?: string | null): string {
  return value
    ? new Intl.DateTimeFormat("pt-BR", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(value))
    : "—";
}

export function InterventionEffectivenessPage() {
  const initial = useMemo(defaultPeriod, []);
  const [periodStart, setPeriodStart] = useState(initial.start);
  const [periodEnd, setPeriodEnd] = useState(initial.end);
  const [windowCode, setWindowCode] = useState("");
  const [windows, setWindows] = useState<EffectivenessWindow[]>([]);
  const [dashboard, setDashboard] =
    useState<EffectivenessDashboard | null>(null);
  const [metrics, setMetrics] = useState<EffectivenessMetric[]>([]);
  const [checkpoints, setCheckpoints] = useState<EvaluationCheckpoint[]>([]);
  const [message, setMessage] = useState("Carregando eficácia longitudinal...");
  const [busy, setBusy] = useState(false);

  async function load(): Promise<void> {
    try {
      const [windowData, dashboardData, metricData, checkpointData] =
        await Promise.all([
          interventionEffectivenessApi.windows(),
          interventionEffectivenessApi.dashboard(periodStart, periodEnd),
          interventionEffectivenessApi.metrics({
            periodStart,
            periodEnd,
            windowCode: windowCode || undefined,
          }),
          interventionEffectivenessApi.checkpoints({
            dueOnly: true,
          }),
        ]);
      setWindows(windowData);
      setDashboard(dashboardData);
      setMetrics(metricData);
      setCheckpoints(checkpointData);
      setMessage("");
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Não foi possível carregar a eficácia das intervenções.",
      );
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function refresh(): Promise<void> {
    setBusy(true);
    setMessage("Avaliando checkpoints e recalculando indicadores...");
    try {
      const result = await interventionEffectivenessApi.refresh({
        period_start: periodStart,
        period_end: periodEnd,
        evaluate_due: true,
        window_code: windowCode || undefined,
      });
      setMessage(
        `${result.metrics_calculated} indicador(es) recalculado(s). ` +
          `${result.interventions_scheduled} intervenção(ões) incluída(s) no acompanhamento.`,
      );
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Não foi possível atualizar os indicadores.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function evaluate(item: EvaluationCheckpoint): Promise<void> {
    setBusy(true);
    try {
      await interventionEffectivenessApi.evaluate(item.id, { force: true });
      setMessage(`Checkpoint ${item.window_code} reavaliado.`);
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Não foi possível avaliar o checkpoint.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function exportCsv(): Promise<void> {
    try {
      const blob = await interventionEffectivenessApi.exportCsv(
        periodStart,
        periodEnd,
        windowCode || undefined,
      );
      const href = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = href;
      anchor.download =
        `eficacia-intervencoes-${periodStart}-${periodEnd}.csv`;
      anchor.click();
      URL.revokeObjectURL(href);
      setMessage("Relatório CSV exportado.");
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Não foi possível exportar o relatório.",
      );
    }
  }

  const overall = metrics.filter(
    (item) =>
      item.dimension_type === "overall" &&
      item.scope_key === "ORGANIZATION",
  );
  const dimensions = metrics.filter(
    (item) => item.dimension_type !== "overall",
  );

  return (
    <section className="effectiveness-page">
      <header className="page-header">
        <div>
          <span className="eyebrow">SPRINT 16.8</span>
          <h1>Eficácia longitudinal das intervenções</h1>
          <p>
            Acompanhe melhoria imediata, retenção em 7, 15, 30 e 60 dias,
            reincidência de alertas e diferenças por recurso pedagógico.
          </p>
        </div>
      </header>

      <section className="panel effectiveness-filters">
        <label>
          Início
          <input
            type="date"
            value={periodStart}
            onChange={(event: ChangeEvent<HTMLInputElement>) => setPeriodStart(event.target.value)}
          />
        </label>
        <label>
          Fim
          <input
            type="date"
            value={periodEnd}
            onChange={(event: ChangeEvent<HTMLInputElement>) => setPeriodEnd(event.target.value)}
          />
        </label>
        <label>
          Janela
          <select
            value={windowCode}
            onChange={(event: ChangeEvent<HTMLSelectElement>) => setWindowCode(event.target.value)}
          >
            <option value="">Todas</option>
            {windows.map((item) => (
              <option value={item.code} key={item.code}>
                {item.code} ({item.days} dias)
              </option>
            ))}
          </select>
        </label>
        <button type="button" disabled={busy} onClick={() => void refresh()}>
          {busy ? "Processando..." : "Atualizar eficácia"}
        </button>
        <button
          className="secondary-button"
          type="button"
          onClick={() => void exportCsv()}
        >
          Exportar CSV
        </button>
      </section>

      {message ? <div className="inline-message">{message}</div> : null}

      {dashboard ? (
        <section className="effectiveness-summary-grid">
          <article className="panel">
            <strong>{dashboard.completed_interventions}</strong>
            <span>intervenções concluídas</span>
          </article>
          <article className="panel">
            <strong>{dashboard.pending_checkpoints}</strong>
            <span>avaliações pendentes</span>
          </article>
          <article className="panel">
            <strong>{dashboard.overdue_checkpoints}</strong>
            <span>avaliações vencidas</span>
          </article>
          <article className="panel">
            <strong>{overall.length}</strong>
            <span>janelas consolidadas</span>
          </article>
        </section>
      ) : null}

      <section className="panel">
        <h2>Visão geral por janela</h2>
        <div className="effectiveness-table-wrap">
          <table className="effectiveness-table">
            <thead>
              <tr>
                <th>Janela</th>
                <th>Amostra</th>
                <th>Melhoria</th>
                <th>Meta</th>
                <th>Retenção</th>
                <th>Reincidência</th>
                <th>Ganho médio</th>
              </tr>
            </thead>
            <tbody>
              {overall.map((item) => (
                <tr key={item.id}>
                  <td>{item.window_code}</td>
                  <td>{item.sample_size}</td>
                  <td>{percentage(item.improved_rate)}</td>
                  <td>{percentage(item.target_met_rate)}</td>
                  <td>{percentage(item.retention_rate)}</td>
                  <td>{percentage(item.recurrence_rate)}</td>
                  <td>{signedPercentage(item.average_gain)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!overall.length ? <p>Atualize os indicadores para gerar a visão geral.</p> : null}
      </section>

      <section className="panel">
        <h2>Eficácia por dimensão</h2>
        <div className="effectiveness-dimension-grid">
          {dimensions.map((item) => (
            <article className="effectiveness-dimension-card" key={item.id}>
              <span>{item.dimension_type} · {item.window_code}</span>
              <h3>{item.dimension_key}</h3>
              {item.privacy_suppressed ? (
                <p>Resultado protegido por grupo pequeno.</p>
              ) : (
                <dl>
                  <div><dt>Amostra</dt><dd>{item.sample_size}</dd></div>
                  <div><dt>Melhoria</dt><dd>{percentage(item.improved_rate)}</dd></div>
                  <div><dt>Retenção</dt><dd>{percentage(item.retention_rate)}</dd></div>
                  <div><dt>Reincidência</dt><dd>{percentage(item.recurrence_rate)}</dd></div>
                </dl>
              )}
            </article>
          ))}
        </div>
        {!dimensions.length ? <p>Nenhuma dimensão agregada no período.</p> : null}
      </section>

      <section className="panel">
        <h2>Checkpoints vencidos ou pendentes</h2>
        <div className="effectiveness-checkpoint-list">
          {checkpoints.map((item) => (
            <article key={item.id}>
              <div>
                <strong>{item.window_code}</strong>
                <span>
                  {item.metric_name} · previsto para {formatDate(item.scheduled_for)}
                </span>
                <small>
                  Estado: {item.status} · evidências: {item.evidence_count}
                </small>
              </div>
              <button
                type="button"
                disabled={busy}
                onClick={() => void evaluate(item)}
              >
                Reavaliar
              </button>
            </article>
          ))}
        </div>
        {!checkpoints.length ? <p>Nenhum checkpoint vencido.</p> : null}
      </section>

      <p className="effectiveness-disclaimer">
        Os indicadores são descritivos. Eles não demonstram causalidade e não
        substituem a análise pedagógica do professor.
      </p>
    </section>
  );
}
