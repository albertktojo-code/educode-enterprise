import {
  useEffect,
  useMemo,
  useState,
  type ChangeEvent,
} from "react";

import { institutionalGovernanceApi } from "./api";
import type {
  GovernanceAsset,
  GovernanceComparison,
  GovernanceDashboard,
  GovernanceIncident,
  GovernanceSnapshot,
} from "./types";
import "./styles.css";

function percentage(value?: number | null): string {
  return value === null || value === undefined
    ? "—"
    : `${(value * 100).toFixed(1)}%`;
}

function formatDate(value?: string | null): string {
  return value
    ? new Intl.DateTimeFormat("pt-BR", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(value))
    : "—";
}

function defaultPeriod(): { start: string; end: string } {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 90);
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  };
}

export function InstitutionalGovernancePage() {
  const initial = useMemo(defaultPeriod, []);
  const [dashboard, setDashboard] =
    useState<GovernanceDashboard | null>(null);
  const [assets, setAssets] = useState<GovernanceAsset[]>([]);
  const [snapshots, setSnapshots] = useState<GovernanceSnapshot[]>([]);
  const [incidents, setIncidents] = useState<GovernanceIncident[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [periodStart, setPeriodStart] = useState(initial.start);
  const [periodEnd, setPeriodEnd] = useState(initial.end);
  const [leftId, setLeftId] = useState("");
  const [rightId, setRightId] = useState("");
  const [comparison, setComparison] =
    useState<GovernanceComparison | null>(null);
  const [message, setMessage] = useState(
    "Carregando governança institucional...",
  );
  const [busy, setBusy] = useState(false);

  async function load(): Promise<void> {
    try {
      const [summary, assetData, snapshotData, incidentData] =
        await Promise.all([
          institutionalGovernanceApi.dashboard(),
          institutionalGovernanceApi.assets({
            status: statusFilter || undefined,
            assetType: typeFilter || undefined,
          }),
          institutionalGovernanceApi.snapshots(false),
          institutionalGovernanceApi.incidents("open"),
        ]);
      setDashboard(summary);
      setAssets(assetData);
      setSnapshots(snapshotData);
      setIncidents(incidentData);
      setMessage("");
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Não foi possível carregar a governança.",
      );
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function bootstrap(): Promise<void> {
    setBusy(true);
    try {
      const result = await institutionalGovernanceApi.bootstrap();
      const total = Object.values(result.created).reduce(
        (sum, value) => sum + value,
        0,
      );
      setMessage(`${total} ativo(s) canônico(s) registrado(s).`);
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Falha no inventário.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function refreshMonitoring(): Promise<void> {
    setBusy(true);
    setMessage("Monitorando qualidade, segurança, eficácia e disparidades...");
    try {
      const result = await institutionalGovernanceApi.refresh({
        period_start: periodStart,
        period_end: periodEnd,
        open_incidents: true,
      });
      setMessage(
        `${result.assets_monitored} ativo(s) monitorado(s); ` +
          `${result.threshold_breaches} ocorrência(s) fora dos limites.`,
      );
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Falha no monitoramento.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function submit(asset: GovernanceAsset): Promise<void> {
    setBusy(true);
    try {
      await institutionalGovernanceApi.submit(asset.id);
      setMessage(`Versão ${asset.version} submetida para revisão.`);
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao submeter.");
    } finally {
      setBusy(false);
    }
  }

  async function review(asset: GovernanceAsset): Promise<void> {
    const stage =
      window.prompt(
        "Etapa: technical, pedagogical, privacy, safety, ethics ou final",
        "technical",
      ) ?? "";
    const decision =
      window.prompt(
        "Decisão: approved, changes_requested ou rejected",
        "approved",
      ) ?? "";
    const comments =
      window.prompt("Comentários da revisão:", "") ?? "";
    if (
      !["approved", "changes_requested", "rejected"].includes(decision)
    ) {
      setMessage("Decisão inválida.");
      return;
    }
    setBusy(true);
    try {
      await institutionalGovernanceApi.review(asset.id, {
        review_stage: stage,
        decision: decision as
          | "approved"
          | "changes_requested"
          | "rejected",
        scorecard: {},
        findings: [],
        required_actions: [],
        comments,
      });
      setMessage("Revisão institucional registrada.");
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Falha ao revisar.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function lifecycleAction(
    asset: GovernanceAsset,
    action: "activate" | "suspend" | "reinstate" | "retire",
  ): Promise<void> {
    const reason = window.prompt("Justificativa da decisão:", "") ?? "";
    if (reason.trim().length < 5) {
      setMessage("Informe uma justificativa com pelo menos cinco caracteres.");
      return;
    }
    setBusy(true);
    try {
      await institutionalGovernanceApi.action(asset.id, action, reason);
      setMessage(`Ação ${action} registrada com auditoria.`);
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Falha na decisão.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function createVersion(asset: GovernanceAsset): Promise<void> {
    const summary =
      window.prompt("Resumo das alterações da nova versão:", "") ?? "";
    if (summary.trim().length < 5) return;
    setBusy(true);
    try {
      await institutionalGovernanceApi.createVersion(asset.id, summary);
      setMessage("Nova versão criada como rascunho.");
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Falha ao criar versão.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function compare(): Promise<void> {
    if (!leftId || !rightId) {
      setMessage("Selecione duas versões para comparar.");
      return;
    }
    try {
      setComparison(
        await institutionalGovernanceApi.compare(leftId, rightId),
      );
      setMessage("");
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Falha na comparação.",
      );
    }
  }

  async function resolveIncident(
    incident: GovernanceIncident,
  ): Promise<void> {
    const summary =
      window.prompt("Resumo da resolução e evidências:", "") ?? "";
    if (summary.trim().length < 5) return;
    setBusy(true);
    try {
      await institutionalGovernanceApi.resolveIncident(
        incident.id,
        summary,
      );
      setMessage("Incidente resolvido. A reativação continua sendo humana.");
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Falha ao resolver.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function exportCsv(): Promise<void> {
    try {
      const blob = await institutionalGovernanceApi.exportCsv();
      const href = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = href;
      anchor.download = "governanca-institucional.csv";
      anchor.click();
      URL.revokeObjectURL(href);
      setMessage("Registro de governança exportado.");
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Falha na exportação.",
      );
    }
  }

  const versionsByCode = useMemo(() => {
    const groups = new Map<string, GovernanceAsset[]>();
    assets.forEach((asset) => {
      const group = groups.get(asset.code) ?? [];
      group.push(asset);
      groups.set(asset.code, group);
    });
    return [...groups.entries()].filter(([, rows]) => rows.length > 1);
  }, [assets]);

  return (
    <section className="governance-page">
      <header className="page-header">
        <div>
          <span className="eyebrow">SPRINT 16.9</span>
          <h1>Governança institucional</h1>
          <p>
            Registro, versionamento, revisão independente, ativação,
            monitoramento, incidentes e suspensão humana de modelos,
            intervenções e regras de evidência.
          </p>
        </div>
      </header>

      {message ? <div className="inline-message">{message}</div> : null}

      {dashboard ? (
        <section className="governance-summary-grid">
          <article className="panel">
            <strong>{dashboard.asset_counts.active ?? 0}</strong>
            <span>ativos em produção</span>
          </article>
          <article className="panel">
            <strong>{dashboard.asset_counts.in_review ?? 0}</strong>
            <span>em revisão</span>
          </article>
          <article className="panel">
            <strong>{dashboard.asset_counts.review_required ?? 0}</strong>
            <span>revisão necessária</span>
          </article>
          <article className="panel">
            <strong>{dashboard.open_incidents}</strong>
            <span>incidentes abertos</span>
          </article>
          <article className="panel">
            <strong>{dashboard.enforcement_mode}</strong>
            <span>modo de enforcement</span>
          </article>
        </section>
      ) : null}

      <section className="panel governance-toolbar">
        <button type="button" disabled={busy} onClick={() => void bootstrap()}>
          Inventariar ativos existentes
        </button>
        <label>
          Início do monitoramento
          <input
            type="date"
            value={periodStart}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setPeriodStart(event.target.value)
            }
          />
        </label>
        <label>
          Fim
          <input
            type="date"
            value={periodEnd}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setPeriodEnd(event.target.value)
            }
          />
        </label>
        <button
          type="button"
          disabled={busy}
          onClick={() => void refreshMonitoring()}
        >
          Atualizar monitoramento
        </button>
        <button
          className="secondary-button"
          type="button"
          onClick={() => void exportCsv()}
        >
          Exportar registro
        </button>
      </section>

      <section className="panel">
        <div className="governance-filter-row">
          <h2>Registro de ativos governados</h2>
          <label>
            Estado
            <select
              value={statusFilter}
              onChange={(event: ChangeEvent<HTMLSelectElement>) =>
                setStatusFilter(event.target.value)
              }
            >
              <option value="">Todos</option>
              {[
                "draft",
                "in_review",
                "approved",
                "active",
                "review_required",
                "suspended",
                "retired",
              ].map((status) => (
                <option value={status} key={status}>{status}</option>
              ))}
            </select>
          </label>
          <label>
            Tipo
            <select
              value={typeFilter}
              onChange={(event: ChangeEvent<HTMLSelectElement>) =>
                setTypeFilter(event.target.value)
              }
            >
              <option value="">Todos</option>
              {[
                "adaptive_model",
                "ai_model",
                "prompt_template",
                "module_policy",
                "intervention_strategy",
                "evidence_rule",
              ].map((type) => (
                <option value={type} key={type}>{type}</option>
              ))}
            </select>
          </label>
          <button type="button" onClick={() => void load()}>
            Aplicar filtros
          </button>
        </div>

        <div className="governance-asset-list">
          {assets.map((asset) => (
            <article className="governance-asset-card" key={asset.id}>
              <div>
                <span>
                  {asset.asset_type} · risco {asset.risk_tier} ·{" "}
                  {asset.status}
                </span>
                <h3>{asset.name}</h3>
                <p>{asset.code} · versão {asset.version}</p>
                <small>
                  Documentação:{" "}
                  {percentage(asset.documentation_completeness)}
                  {asset.review_summary
                    ? ` · aprovações ${asset.review_summary.approval_count}/${asset.review_summary.required_approvals}`
                    : ""}
                </small>
              </div>
              <div className="governance-action-row">
                {["draft", "changes_requested"].includes(asset.status) ? (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void submit(asset)}
                  >
                    Submeter
                  </button>
                ) : null}
                {asset.status === "in_review" ? (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void review(asset)}
                  >
                    Revisar
                  </button>
                ) : null}
                {asset.status === "approved" ? (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void lifecycleAction(asset, "activate")}
                  >
                    Ativar
                  </button>
                ) : null}
                {["active", "review_required", "approved"].includes(
                  asset.status,
                ) ? (
                  <button
                    className="danger-button"
                    type="button"
                    disabled={busy}
                    onClick={() => void lifecycleAction(asset, "suspend")}
                  >
                    Suspender
                  </button>
                ) : null}
                {asset.status === "suspended" ? (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void lifecycleAction(asset, "reinstate")}
                  >
                    Reativar
                  </button>
                ) : null}
                {asset.status !== "retired" ? (
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={busy}
                    onClick={() => void createVersion(asset)}
                  >
                    Nova versão
                  </button>
                ) : null}
              </div>
            </article>
          ))}
        </div>
        {!assets.length ? <p>Nenhum ativo registrado.</p> : null}
      </section>

      <section className="panel">
        <h2>Comparação entre versões</h2>
        <div className="governance-compare-row">
          <select
            value={leftId}
            onChange={(event: ChangeEvent<HTMLSelectElement>) =>
              setLeftId(event.target.value)
            }
          >
            <option value="">Versão A</option>
            {versionsByCode.flatMap(([, rows]) =>
              rows.map((asset) => (
                <option value={asset.id} key={`left-${asset.id}`}>
                  {asset.code} v{asset.version}
                </option>
              )),
            )}
          </select>
          <select
            value={rightId}
            onChange={(event: ChangeEvent<HTMLSelectElement>) =>
              setRightId(event.target.value)
            }
          >
            <option value="">Versão B</option>
            {versionsByCode.flatMap(([, rows]) =>
              rows.map((asset) => (
                <option value={asset.id} key={`right-${asset.id}`}>
                  {asset.code} v{asset.version}
                </option>
              )),
            )}
          </select>
          <button type="button" onClick={() => void compare()}>
            Comparar
          </button>
        </div>
        {comparison ? (
          <div className="governance-comparison">
            <article>
              <strong>v{comparison.left.version}</strong>
              <span>{comparison.left.status}</span>
              <small>
                documentação{" "}
                {percentage(
                  comparison.left.documentation_completeness,
                )}
              </small>
            </article>
            <article>
              <strong>v{comparison.right.version}</strong>
              <span>{comparison.right.status}</span>
              <small>
                documentação{" "}
                {percentage(
                  comparison.right.documentation_completeness,
                )}
              </small>
            </article>
            <p>
              Campos alterados:{" "}
              {comparison.documentation_diff.changed_keys.join(", ") ||
                "nenhum"}
            </p>
          </div>
        ) : null}
      </section>

      <section className="panel">
        <h2>Monitoramento mais recente</h2>
        <div className="governance-snapshot-grid">
          {snapshots.slice(0, 30).map((snapshot) => (
            <article key={snapshot.id}>
              <span>
                {snapshot.period_start} a {snapshot.period_end}
              </span>
              <strong>
                {snapshot.threshold_breached
                  ? "Revisão necessária"
                  : "Dentro dos limites"}
              </strong>
              {snapshot.privacy_suppressed ? (
                <p>Indicadores protegidos por amostra pequena.</p>
              ) : (
                <dl>
                  <div><dt>Qualidade</dt><dd>{percentage(snapshot.quality_score)}</dd></div>
                  <div><dt>Segurança</dt><dd>{percentage(snapshot.safety_score)}</dd></div>
                  <div><dt>Eficácia</dt><dd>{percentage(snapshot.effectiveness_score)}</dd></div>
                  <div><dt>Equidade contextual</dt><dd>{percentage(snapshot.fairness_score)}</dd></div>
                  <div><dt>Erro</dt><dd>{percentage(snapshot.error_rate)}</dd></div>
                </dl>
              )}
              <small>{formatDate(snapshot.calculated_at)}</small>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>Incidentes abertos</h2>
        <div className="governance-incident-list">
          {incidents.map((incident) => (
            <article key={incident.id}>
              <div>
                <span>{incident.severity} · {incident.category}</span>
                <h3>{incident.title}</h3>
                <p>{incident.description}</p>
                <small>{formatDate(incident.detected_at)}</small>
              </div>
              <button
                type="button"
                disabled={busy}
                onClick={() => void resolveIncident(incident)}
              >
                Registrar resolução
              </button>
            </article>
          ))}
        </div>
        {!incidents.length ? <p>Nenhum incidente aberto.</p> : null}
      </section>

      <p className="governance-disclaimer">
        O monitoramento automático pode exigir revisão, mas não suspende
        modelos ou estratégias sem decisão humana registrada.
      </p>
    </section>
  );
}
