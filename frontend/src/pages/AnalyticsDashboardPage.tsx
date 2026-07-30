import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'
import type { AttemptPolicy, DashboardSummary, DataQuality, LearningAlert } from '../types/analytics'
import type { AssignmentSummary } from '../types/delivery'
import type { Classroom } from '../types/education'

const policyLabels: Record<AttemptPolicy, string> = {
  first: 'Primeira tentativa',
  latest: 'Última tentativa',
  best: 'Melhor tentativa',
  all: 'Todas as tentativas',
}

function value(value: number | null, suffix = '%') {
  return value === null ? 'Sem dados' : `${value.toFixed(1)}${suffix}`
}

export function AnalyticsDashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [quality, setQuality] = useState<DataQuality | null>(null)
  const [alerts, setAlerts] = useState<LearningAlert[]>([])
  const [classrooms, setClassrooms] = useState<Classroom[]>([])
  const [assignments, setAssignments] = useState<AssignmentSummary[]>([])
  const [policy, setPolicy] = useState<AttemptPolicy>('best')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  async function load(currentPolicy: AttemptPolicy = policy) {
    const [summaryData, qualityData, alertData, classroomData, assignmentData] = await Promise.all([
      api<DashboardSummary>(`/analytics/dashboard?attempt_policy=${currentPolicy}`),
      api<DataQuality>('/analytics/data-quality'),
      api<LearningAlert[]>('/analytics/alerts?status=open'),
      api<Classroom[]>('/classrooms'),
      api<AssignmentSummary[]>('/delivery/assignments'),
    ])
    setSummary(summaryData)
    setQuality(qualityData)
    setAlerts(alertData.slice(0, 6))
    setClassrooms(classroomData.filter((item) => item.is_active))
    setAssignments(assignmentData)
  }

  useEffect(() => { void load().catch((error: Error) => setMessage(error.message)) }, [])

  async function changePolicy(next: AttemptPolicy) {
    setPolicy(next)
    await load(next)
  }

  async function refresh() {
    setBusy(true); setMessage('')
    try {
      await api('/analytics/refresh', {
        method: 'POST',
        body: JSON.stringify({ attempt_policy: policy, create_snapshots: true, generate_alerts: true }),
      })
      await load(policy)
      setMessage('Indicadores atualizados e alertas recalculados.')
    } catch (error) { setMessage((error as Error).message) } finally { setBusy(false) }
  }

  return (
    <section>
      <header className="page-header analytics-header">
        <div><span className="eyebrow">LEARNING ANALYTICS</span><h1>Evolução da aprendizagem</h1><p>Entenda o progresso, identifique dificuldades e planeje intervenções com critérios transparentes.</p></div>
        <div className="analytics-actions"><a className="secondary-button" href="/ia?module=analytics&action=suggest_intervention">Sugerir intervenção com IA</a>
          <label>Considerar<select value={policy} onChange={(event) => void changePolicy(event.target.value as AttemptPolicy)}>{Object.entries(policyLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          <button className="primary-button" disabled={busy} onClick={() => void refresh()} type="button">{busy ? 'Atualizando...' : 'Atualizar indicadores'}</button>
        </div>
      </header>
      {message ? <div className="inline-message">{message}</div> : null}

      <div className="analytics-card-grid">
        <article className="metric-card"><span>Estudantes avaliados</span><strong>{summary?.students_count ?? 0}</strong><small>com tentativas válidas</small></article>
        <article className="metric-card"><span>Média geral</span><strong>{value(summary?.average_percentage ?? null)}</strong><small>{policyLabels[policy].toLowerCase()}</small></article>
        <article className="metric-card"><span>Conclusão</span><strong>{value(summary?.completion_rate ?? null)}</strong><small>publicações concluídas</small></article>
        <article className="metric-card metric-attention"><span>Precisam de atenção</span><strong>{summary?.students_needing_attention ?? 0}</strong><small>alertas explicáveis</small></article>
        <article className="metric-card"><span>Questões difíceis</span><strong>{summary?.difficult_questions ?? 0}</strong><small>acerto abaixo de 40%</small></article>
        <article className="metric-card"><span>Correções pendentes</span><strong>{summary?.pending_manual_grading ?? 0}</strong><small>respostas discursivas</small></article>
      </div>

      <div className="analytics-two-columns">
        <article className="panel">
          <div className="panel-title-row"><div><h2>Turmas</h2><p>Abra uma turma para ver estudantes, tendências, BNCC e Pensamento Computacional.</p></div></div>
          <div className="analytics-link-list">
            {classrooms.map((item) => <Link key={item.id} to={`/analytics/turmas/${item.id}`}><span><strong>{item.name}</strong><small>{item.grade || 'Ano não informado'}</small></span><b>Ver evolução →</b></Link>)}
            {!classrooms.length ? <p className="muted">Nenhuma turma ativa.</p> : null}
          </div>
        </article>
        <article className="panel">
          <div className="panel-title-row"><div><h2>Atividades recentes</h2><p>Analise questões, distratores, tempo e taxa de acerto.</p></div></div>
          <div className="analytics-link-list">
            {assignments.slice(0, 8).map((item) => <Link key={item.id} to={`/analytics/atividades/${item.id}`}><span><strong>{item.title}</strong><small>{item.status}</small></span><b>Analisar →</b></Link>)}
            {!assignments.length ? <p className="muted">Nenhuma publicação encontrada.</p> : null}
          </div>
        </article>
      </div>

      <div className="analytics-two-columns">
        <article className="panel">
          <div className="panel-title-row"><div><h2>Alertas pedagógicos</h2><p>Todos os alertas mostram a regra e as evidências utilizadas.</p></div><Link to="/analytics/alertas">Ver todos</Link></div>
          <div className="alert-stack">
            {alerts.map((alert) => <article className={`learning-alert severity-${alert.severity}`} key={alert.id}><div><span>{alert.severity}</span><h3>{alert.title}</h3><p>{alert.description}</p><small>{alert.explanation}</small></div></article>)}
            {!alerts.length ? <p className="muted">Nenhum alerta aberto.</p> : null}
          </div>
        </article>
        <article className="panel data-quality-panel">
          <h2>Qualidade dos dados</h2>
          <div className={`quality-status quality-${quality?.status ?? 'good'}`}>{quality?.status === 'attention' ? 'Atenção' : 'Boa'}</div>
          <dl><div><dt>Tentativas válidas</dt><dd>{quality?.valid_attempts ?? 0}</dd></div><div><dt>Em andamento</dt><dd>{quality?.incomplete_attempts ?? 0}</dd></div><div><dt>Omissões</dt><dd>{quality?.unanswered_items ?? 0}</dd></div><div><dt>Correções manuais</dt><dd>{quality?.manually_graded_answers ?? 0}</dd></div></dl>
          {quality?.notes.map((note) => <p className="quality-note" key={note}>{note}</p>)}
        </article>
      </div>
    </section>
  )
}
