import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import { Link, useParams } from "react-router-dom";

import { comicPageEditorApi } from "./api";
import type {
  HQMonitoringPresence,
  HQMonitoringSnapshot,
  HQMonitoringStudent,
} from "./types";
import "./monitoring.css";

const STATUS_LABELS: Record<HQMonitoringPresence, string> = {
  NOT_STARTED: "Não iniciou",
  STARTED: "Iniciou",
  READING: "Lendo",
  ANSWERING: "Respondendo",
  PAUSED: "Pausado",
  COMPLETED: "Concluiu",
};

function elapsedLabel(seconds: number | null): string {
  if (seconds === null) return "Sem interação registrada";
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}min`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}min`;
}

export function TeacherMonitoringPage() {
  const { deliveryId = "" } = useParams();
  const [snapshot, setSnapshot] =
    useState<HQMonitoringSnapshot | null>(null);
  const [classroomId, setClassroomId] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [studentFilter, setStudentFilter] = useState("");
  const [idleThreshold, setIdleThreshold] = useState(180);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedId, setSelectedId] = useState("");
  const [teacherMessage, setTeacherMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(
    async (initial = false) => {
      if (!deliveryId) return;
      if (initial) setLoading(true);
      else setRefreshing(true);
      try {
        const result = await comicPageEditorApi.monitorActivityDelivery(
          deliveryId,
          {
            classroomId: classroomId || undefined,
            status: statusFilter || undefined,
            idleThresholdSeconds: idleThreshold,
          },
        );
        setSnapshot(result);
        setError("");
      } catch (caught) {
        setError(
          caught instanceof Error
            ? caught.message
            : "Não foi possível atualizar o monitoramento.",
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [classroomId, deliveryId, idleThreshold, statusFilter],
  );

  useEffect(() => {
    void load(true);
  }, [load]);

  useEffect(() => {
    if (!autoRefresh) return;
    const intervalSeconds =
      snapshot?.monitoring.poll_after_seconds ?? 5;
    const timer = window.setInterval(
      () => void load(),
      intervalSeconds * 1000,
    );
    return () => window.clearInterval(timer);
  }, [autoRefresh, load, snapshot?.monitoring.poll_after_seconds]);

  const students = useMemo(() => {
    const normalized = studentFilter.trim().toLocaleLowerCase("pt-BR");
    if (!normalized) return snapshot?.students ?? [];
    return (snapshot?.students ?? []).filter(
      (student) =>
        student.student_name
          .toLocaleLowerCase("pt-BR")
          .includes(normalized) ||
        student.student_id.toLowerCase().includes(normalized),
    );
  }, [snapshot?.students, studentFilter]);

  const selected =
    snapshot?.students.find(
      (student) => student.student_id === selectedId,
    ) ?? null;

  async function runAction(
    student: HQMonitoringStudent,
    action:
      | "PAUSE"
      | "RESUME"
      | "EXTEND"
      | "GRANT_ATTEMPT"
      | "SEND_MESSAGE"
      | "RELEASE_HINT"
      | "RELEASE_ANSWER_KEY",
    payload: Record<string, unknown> = {},
  ): Promise<void> {
    if (!student.session_id) return;
    setActionBusy(true);
    setNotice("");
    setError("");
    try {
      await comicPageEditorApi.teacherDeliveryAction(
        student.session_id,
        {
          action,
          reason: String(
            payload.reason ??
              `Ação docente ${action.toLocaleLowerCase("pt-BR")}`,
          ),
          extra_minutes: Number(payload.extra_minutes ?? 0),
          additional_attempts: Number(
            payload.additional_attempts ?? 0,
          ),
          message:
            typeof payload.message === "string"
              ? payload.message
              : undefined,
          activity_id:
            typeof payload.activity_id === "string"
              ? payload.activity_id
              : undefined,
          hint_level:
            typeof payload.hint_level === "number"
              ? payload.hint_level
              : undefined,
        },
      );
      setTeacherMessage("");
      setNotice("Ação registrada e enviada ao estudante.");
      await load();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Não foi possível registrar a ação docente.",
      );
    } finally {
      setActionBusy(false);
    }
  }

  if (loading && !snapshot) {
    return (
      <main className="hq-monitoring-state" aria-live="polite">
        Carregando monitoramento docente…
      </main>
    );
  }

  if (!snapshot) {
    return (
      <main className="hq-monitoring-state" aria-live="assertive">
        <p>{error || "Monitoramento indisponível."}</p>
        <button type="button" onClick={() => void load(true)}>
          Tentar novamente
        </button>
      </main>
    );
  }

  return (
    <main className="hq-monitoring-page">
      <header className="hq-monitoring-header">
        <div>
          <p className="hq-monitoring-eyebrow">Sprint 16.11.6</p>
          <h1>Monitoramento docente</h1>
          <p>
            {snapshot.delivery.title} · presença e progresso com
            atualização autenticada.
          </p>
        </div>
        <div className="hq-monitoring-header-actions">
          <Link to="/teacher/comic-studio">
            Voltar ao estúdio
          </Link>
          <button
            type="button"
            disabled={refreshing}
            onClick={() => void load()}
          >
            {refreshing ? "Atualizando…" : "Atualizar agora"}
          </button>
        </div>
      </header>

      <p className="hq-monitoring-live" aria-live="polite">
        {error ||
          notice ||
          `Atualizado em ${new Date(
            snapshot.monitoring.last_updated_at,
          ).toLocaleTimeString("pt-BR")}.`}
      </p>

      <section
        className="hq-monitoring-summary"
        aria-label="Resumo da aplicação"
      >
        <article>
          <strong>{snapshot.summary.started}</strong>
          <span>iniciaram</span>
        </article>
        <article>
          <strong>{snapshot.summary.active}</strong>
          <span>ativos agora</span>
        </article>
        <article>
          <strong>{snapshot.summary.completed}</strong>
          <span>concluíram</span>
        </article>
        <article>
          <strong>{snapshot.summary.attention}</strong>
          <span>pedem atenção</span>
        </article>
        <article>
          <strong>{snapshot.summary.average_progress}%</strong>
          <span>progresso médio</span>
        </article>
      </section>

      <section
        className="hq-monitoring-filters"
        aria-labelledby="monitoring-filter-title"
      >
        <h2 id="monitoring-filter-title">Filtros e atualização</h2>
        <label>
          Turma
          <select
            value={classroomId}
            onChange={(event) => setClassroomId(event.target.value)}
          >
            <option value="">Todas as turmas</option>
            {snapshot.filters.classrooms.map((classroom) => (
              <option key={classroom.id} value={classroom.id}>
                {classroom.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Situação
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            <option value="">Todas</option>
            {Object.entries(STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Estudante
          <input
            type="search"
            value={studentFilter}
            placeholder="Nome ou identificador"
            onChange={(event) => setStudentFilter(event.target.value)}
          />
        </label>
        <label>
          Alerta sem interação
          <select
            value={idleThreshold}
            onChange={(event) =>
              setIdleThreshold(Number(event.target.value))
            }
          >
            <option value={60}>1 minuto</option>
            <option value={180}>3 minutos</option>
            <option value={300}>5 minutos</option>
            <option value={600}>10 minutos</option>
          </select>
        </label>
        <label className="hq-monitoring-toggle">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(event) => setAutoRefresh(event.target.checked)}
          />
          Atualizar a cada 5 segundos
        </label>
      </section>

      <div className="hq-monitoring-layout">
        <section
          className="hq-monitoring-table-panel"
          aria-labelledby="monitoring-students-title"
        >
          <header>
            <h2 id="monitoring-students-title">
              Estudantes ({students.length})
            </h2>
            <span>
              Respostas e detalhes do dispositivo não são exibidos.
            </span>
          </header>
          {students.length ? (
            <div className="hq-monitoring-table-wrap">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Estudante</th>
                    <th scope="col">Situação</th>
                    <th scope="col">Local atual</th>
                    <th scope="col">Progresso</th>
                    <th scope="col">Sem interação</th>
                    <th scope="col">Alertas</th>
                    <th scope="col">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((student) => (
                    <tr
                      key={student.student_id}
                      className={
                        selectedId === student.student_id
                          ? "is-selected"
                          : ""
                      }
                    >
                      <td>
                        <strong>{student.student_name}</strong>
                        <small>
                          {student.classroom_names.join(", ") ||
                            "Público individual"}
                        </small>
                      </td>
                      <td>
                        <span
                          className={`hq-presence hq-presence--${student.presence_status.toLowerCase()}`}
                        >
                          {STATUS_LABELS[student.presence_status]}
                        </span>
                      </td>
                      <td>
                        {student.presence_status === "READING"
                          ? `Página ${student.current_page_number ?? "—"}`
                          : student.current_activity_title ??
                            "Ainda sem posição"}
                        {student.current_activity_difficulty ? (
                          <small>
                            Dificuldade prevista:{" "}
                            {student.current_activity_difficulty}
                          </small>
                        ) : null}
                      </td>
                      <td>
                        <progress
                          max={100}
                          value={student.combined_progress}
                          aria-label={`Progresso de ${student.student_name}`}
                        />
                        <small>{student.combined_progress}%</small>
                      </td>
                      <td>
                        <span
                          className={
                            student.is_idle ? "is-idle" : undefined
                          }
                        >
                          {elapsedLabel(student.idle_seconds)}
                        </span>
                      </td>
                      <td>
                        {student.alerts.length ? (
                          <ul className="hq-monitoring-alerts">
                            {student.alerts.map((alert) => (
                              <li key={alert.code}>{alert.message}</li>
                            ))}
                          </ul>
                        ) : (
                          "Sem alertas"
                        )}
                      </td>
                      <td>
                        <button
                          type="button"
                          onClick={() =>
                            setSelectedId(student.student_id)
                          }
                        >
                          Acompanhar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="hq-monitoring-empty">
              Nenhum estudante corresponde aos filtros selecionados.
            </p>
          )}
        </section>

        <aside
          className="hq-monitoring-actions"
          aria-labelledby="monitoring-actions-title"
        >
          <h2 id="monitoring-actions-title">Ações docentes</h2>
          {selected ? (
            <>
              <div>
                <strong>{selected.student_name}</strong>
                <p>
                  Tentativas: {selected.attempts_used} de{" "}
                  {selected.attempts_allowed}
                </p>
              </div>
              <div className="hq-monitoring-action-grid">
                <button
                  type="button"
                  disabled={
                    actionBusy ||
                    !selected.session_id ||
                    selected.presence_status === "PAUSED" ||
                    selected.presence_status === "COMPLETED"
                  }
                  onClick={() =>
                    void runAction(selected, "PAUSE", {
                      reason: "Pausa solicitada pelo professor.",
                    })
                  }
                >
                  Pausar
                </button>
                <button
                  type="button"
                  disabled={
                    actionBusy ||
                    !selected.session_id ||
                    selected.presence_status !== "PAUSED"
                  }
                  onClick={() =>
                    void runAction(selected, "RESUME", {
                      reason: "Retomada liberada pelo professor.",
                    })
                  }
                >
                  Retomar
                </button>
                <button
                  type="button"
                  disabled={actionBusy || !selected.session_id}
                  onClick={() =>
                    void runAction(selected, "EXTEND", {
                      reason: "Tempo adicional concedido pelo professor.",
                      extra_minutes: 10,
                    })
                  }
                >
                  +10 min
                </button>
                <button
                  type="button"
                  disabled={actionBusy || !selected.session_id}
                  onClick={() =>
                    void runAction(selected, "GRANT_ATTEMPT", {
                      reason:
                        "Nova tentativa concedida após revisão docente.",
                      additional_attempts: 1,
                    })
                  }
                >
                  Nova tentativa
                </button>
              </div>

              <label>
                Mensagem para o estudante
                <textarea
                  maxLength={500}
                  value={teacherMessage}
                  onChange={(event) =>
                    setTeacherMessage(event.target.value)
                  }
                  placeholder="Escreva uma orientação objetiva."
                />
              </label>
              <button
                type="button"
                disabled={
                  actionBusy ||
                  !selected.session_id ||
                  teacherMessage.trim().length === 0
                }
                onClick={() =>
                  void runAction(selected, "SEND_MESSAGE", {
                    reason: "Orientação docente durante a aplicação.",
                    message: teacherMessage.trim(),
                  })
                }
              >
                Enviar mensagem
              </button>

              <button
                type="button"
                disabled={
                  actionBusy ||
                  !selected.session_id ||
                  !selected.current_activity_id ||
                  !selected.support.next_hint
                }
                onClick={() => {
                  const hint = selected.support.next_hint;
                  if (!hint || !selected.current_activity_id) return;
                  void runAction(selected, "RELEASE_HINT", {
                    reason: "Dica graduada liberada pelo professor.",
                    message: hint.message,
                    activity_id: selected.current_activity_id,
                    hint_level: hint.level,
                  });
                }}
              >
                {selected.support.next_hint
                  ? `Liberar ${selected.support.next_hint.label ?? "próxima dica"}`
                  : "Sem nova dica aprovada"}
              </button>

              <button
                type="button"
                disabled={
                  actionBusy ||
                  !selected.session_id ||
                  selected.support.answer_key_released
                }
                onClick={() => {
                  if (
                    window.confirm(
                      "Liberar o gabarito para este estudante? A ação será auditada.",
                    )
                  ) {
                    void runAction(
                      selected,
                      "RELEASE_ANSWER_KEY",
                      {
                        reason:
                          "Gabarito liberado após decisão docente.",
                      },
                    );
                  }
                }}
              >
                {selected.support.answer_key_released
                  ? "Gabarito já liberado"
                  : "Liberar gabarito"}
              </button>
            </>
          ) : (
            <p>
              Selecione “Acompanhar” para acessar ações individualizadas.
            </p>
          )}
        </aside>
      </div>

      <section className="hq-monitoring-privacy">
        <h2>Privacidade e decisão humana</h2>
        <p>{snapshot.privacy.message}</p>
        <p>
          Alertas são sinais descritivos: o professor revisa o contexto
          antes de agir. Não há ranking, webcam ou decisão automática.
        </p>
      </section>
    </main>
  );
}
