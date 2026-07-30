import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { interventionOrchestrationApi } from "./api";
import type {
  InterventionAlert,
  InterventionDashboard,
  InterventionProposal,
  InterventionTimelineEvent,
  LearningIntervention,
} from "./types";
import "./styles.css";

function formatDate(value?: string | null): string {
  return value
    ? new Intl.DateTimeFormat("pt-BR", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(value))
    : "não definido";
}

export function InterventionOrchestrationPage() {
  const [dashboard, setDashboard] = useState<InterventionDashboard | null>(null);
  const [alerts, setAlerts] = useState<InterventionAlert[]>([]);
  const [proposals, setProposals] = useState<InterventionProposal[]>([]);
  const [interventions, setInterventions] = useState<LearningIntervention[]>([]);
  const [timeline, setTimeline] = useState<InterventionTimelineEvent[]>([]);
  const [selectedInterventionId, setSelectedInterventionId] = useState<string>("");
  const [message, setMessage] = useState<string>("Carregando intervenções...");
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load(): Promise<void> {
    try {
      const [summary, alertData, proposalData, interventionData] =
        await Promise.all([
          interventionOrchestrationApi.dashboard(),
          interventionOrchestrationApi.alerts(),
          interventionOrchestrationApi.proposals(),
          interventionOrchestrationApi.interventions(),
        ]);
      setDashboard(summary);
      setAlerts(alertData);
      setProposals(proposalData);
      setInterventions(interventionData);
      setMessage("");
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Não foi possível carregar as intervenções.",
      );
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function createProposal(alert: InterventionAlert): Promise<void> {
    setBusyId(alert.id);
    try {
      await interventionOrchestrationApi.createProposal(alert.id, {
        use_ai: true,
        due_days: 7,
        evaluation_days: 7,
        teacher_note: "Revisar a proposta e adaptar a linguagem ao estudante.",
        target_mastery: 0.75,
      });
      setMessage("Proposta criada. A aplicação depende de revisão docente.");
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Falha ao criar proposta.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function reviewProposal(
    proposal: InterventionProposal,
    decision: "approved" | "rejected",
  ): Promise<void> {
    const notes =
      window.prompt(
        decision === "approved"
          ? "Observações da aprovação:"
          : "Motivo da rejeição:",
        "",
      ) ?? "";
    setBusyId(proposal.id);
    try {
      await interventionOrchestrationApi.reviewProposal(proposal.id, {
        decision,
        review_notes: notes,
        due_days: 7,
        evaluation_days: 7,
        create_adaptive_path: decision === "approved",
      });
      setMessage(
        decision === "approved"
          ? "Intervenção aprovada e planejada."
          : "Proposta rejeitada.",
      );
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Falha ao revisar proposta.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function activate(item: LearningIntervention): Promise<void> {
    setBusyId(item.id);
    try {
      await interventionOrchestrationApi.transition(item.id, "active");
      setMessage("Intervenção iniciada.");
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Falha ao iniciar intervenção.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function cancel(item: LearningIntervention): Promise<void> {
    const notes = window.prompt("Justificativa do cancelamento:", "") ?? "";
    setBusyId(item.id);
    try {
      await interventionOrchestrationApi.transition(
        item.id,
        "canceled",
        notes,
      );
      setMessage("Intervenção cancelada com registro de histórico.");
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Falha ao cancelar intervenção.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function complete(item: LearningIntervention): Promise<void> {
    const result = window.prompt(
      "Resumo do resultado observado:",
      "Intervenção concluída e revisada pelo professor.",
    );
    if (!result) return;
    setBusyId(item.id);
    try {
      const response = await interventionOrchestrationApi.complete(item.id, {
        result_summary: result,
        teacher_notes: "",
      });
      if (response.outcome.comparable === false) {
        setMessage(
          "Intervenção concluída, mas o alerta foi reaberto por falta de evidência comparável.",
        );
      } else {
        const gain = ((response.outcome.gain ?? 0) * 100).toFixed(1);
        const suffix =
          response.outcome.target_met || response.outcome.improved
            ? " Alerta resolvido."
            : " Alerta reaberto para revisão.";
        setMessage(
          `Resultado registrado: ${response.outcome.outcome ?? "estável"}, variação ${gain} p.p.${suffix}`,
        );
      }
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Falha ao concluir intervenção.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function openTimeline(item: LearningIntervention): Promise<void> {
    setSelectedInterventionId(item.id);
    try {
      setTimeline(await interventionOrchestrationApi.timeline(item.id));
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Falha ao carregar histórico.",
      );
    }
  }

  return (
    <section className="intervention-orchestration-page">
      <header className="page-header">
        <div>
          <span className="eyebrow">SPRINT 16.8</span>
          <h1>Intervenções pedagógicas com HQs</h1>
          <p>
            Evidências, sugestões explicáveis, revisão humana, atribuição e
            comparação de resultados.
          </p>
        </div>
        <Link to="/teacher/intervention-effectiveness">
          Avaliar eficácia longitudinal
        </Link>
      </header>

      {message ? <div className="inline-message">{message}</div> : null}

      {dashboard !== null ? (
        <div className="intervention-metric-grid">
          <article className="panel">
            <strong>{dashboard.open_alerts}</strong><span>alertas abertos</span>
          </article>
          <article className="panel">
            <strong>{dashboard.pending_proposals}</strong><span>propostas pendentes</span>
          </article>
          <article className="panel">
            <strong>{dashboard.planned_interventions}</strong><span>planejadas</span>
          </article>
          <article className="panel">
            <strong>{dashboard.active_interventions}</strong><span>em execução</span>
          </article>
          <article className="panel">
            <strong>{dashboard.overdue_interventions}</strong><span>atrasadas</span>
          </article>
        </div>
      ) : null}

      <section className="panel">
        <h2>Alertas elegíveis</h2>
        <p>
          A IA pode elaborar um rascunho, mas nenhuma intervenção é aplicada
          sem aprovação docente.
        </p>
        <div className="intervention-card-list">
          {alerts.map((alert) => (
            <article className="intervention-card" key={alert.id}>
              <div>
                <span>{alert.severity} · {alert.status}</span>
                <h3>{alert.title}</h3>
                <p>{alert.description}</p>
                <small>{alert.explanation}</small>
              </div>
              <button
                type="button"
                disabled={alert.has_proposal || busyId === alert.id}
                onClick={() => void createProposal(alert)}
              >
                {alert.has_proposal
                  ? "Proposta existente"
                  : busyId === alert.id
                    ? "Gerando..."
                    : "Gerar proposta revisável"}
              </button>
            </article>
          ))}
          {!alerts.length ? <p>Nenhum alerta elegível.</p> : null}
        </div>
      </section>

      <section className="panel">
        <h2>Caixa de revisão docente</h2>
        <div className="intervention-card-list">
          {proposals.map((proposal) => (
            <article className="intervention-card" key={proposal.id}>
              <div>
                <span>
                  {proposal.priority} · confiança{" "}
                  {Math.round(proposal.confidence_score * 100)}%
                  {proposal.created_by_ai
                    ? " · conteúdo incorporado da IA"
                    : proposal.ai_requested
                      ? " · IA solicitada; proposta ainda determinística"
                      : ""}
                </span>
                <h3>{proposal.title}</h3>
                <p>{proposal.rationale}</p>
                <small>
                  {proposal.proposed_materials.length} ação(ões) propostas ·{" "}
                  {proposal.status}
                </small>
              </div>
              {proposal.status === "pending_review" ? (
                <div className="button-row">
                  <button
                    type="button"
                    disabled={busyId === proposal.id}
                    onClick={() => void reviewProposal(proposal, "approved")}
                  >
                    Aprovar e planejar
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={busyId === proposal.id}
                    onClick={() => void reviewProposal(proposal, "rejected")}
                  >
                    Rejeitar
                  </button>
                </div>
              ) : null}
            </article>
          ))}
          {!proposals.length ? <p>Nenhuma proposta registrada.</p> : null}
        </div>
      </section>

      <section className="panel">
        <h2>Intervenções acompanhadas</h2>
        <div className="intervention-card-list">
          {interventions.map((item) => (
            <article className="intervention-card" key={item.id}>
              <div>
                <span>{item.intervention_type} · {item.status}</span>
                <h3>{item.expected_outcome}</h3>
                <p>{item.reason}</p>
                <small>
                  Prazo: {formatDate(item.due_at)}
                  {item.adaptive_path_id ? " · trilha adaptativa vinculada" : ""}
                </small>
              </div>
              <div className="button-row">
                {item.status === "planned" ? (
                  <button
                    type="button"
                    disabled={busyId === item.id}
                    onClick={() => void activate(item)}
                  >
                    Iniciar
                  </button>
                ) : null}
                {item.status === "active" ? (
                  <button
                    type="button"
                    disabled={busyId === item.id}
                    onClick={() => void complete(item)}
                  >
                    Concluir e avaliar
                  </button>
                ) : null}
                {["planned", "active"].includes(item.status) ? (
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={busyId === item.id}
                    onClick={() => void cancel(item)}
                  >
                    Cancelar
                  </button>
                ) : null}
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => void openTimeline(item)}
                >
                  Histórico
                </button>
              </div>
            </article>
          ))}
          {!interventions.length ? <p>Nenhuma intervenção acompanhada.</p> : null}
        </div>
      </section>

      {selectedInterventionId ? (
        <section className="panel">
          <h2>Linha do tempo</h2>
          <div className="intervention-timeline">
            {timeline.map((event) => (
              <article key={event.id}>
                <strong>{event.event_type}</strong>
                <span>
                  {event.from_status || "—"} → {event.to_status || "—"}
                </span>
                <small>{formatDate(event.created_at)}</small>
              </article>
            ))}
            {!timeline.length ? <p>Nenhum evento registrado.</p> : null}
          </div>
        </section>
      ) : null}
    </section>
  );
}
