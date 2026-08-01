import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { EmptyState } from '../components/EmptyState'
import { LoadingState } from '../components/LoadingState'
import { StatusCard } from '../components/StatusCard'
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
  const [loading, setLoading] = useState(true)

  async function load(currentPolicy: AttemptPolicy = policy) {
    setLoading(true)
    try {
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
    } finally {
      setLoading(false)
    }
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
        <div className="analytics-actions"><Link className="secondary-button" to="/ia?module=analytics&action=suggest_intervention">Sugerir intervenção com IA</Link>
          <label>Considerar<select value={policy} onChange={(event) => void changePolicy(event.target.value as AttemptPolicy)}>{Object.entries(policyLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          <button className="primary-button" disabled={busy} onClick={() => void refresh()} type="button">{busy ? 'Atualizando...' : 'Atualizar indicadores'}</button>
        </div>
      </header>
      {message ? <div className="inline-message" role="status">{message}</div> : null}

      <div className="data-metric-grid data-metric-grid--six" aria-label="Indicadores de aprendizagem">
        <StatusCard title="Estudantes avaliados" value={summary?.students_count ?? 0} detail="com tentativas válidas" state="info" loading={loading} />
        <StatusCard title="Média geral" value={value(summary?.average_percentage ?? null)} detail={policyLabels[policy].toLowerCase()} state="success" loading={loading} />
        <StatusCard title="Conclusão" value={value(summary?.completion_rate ?? null)} detail="publicações concluídas" state="success" loading={loading} />
        <StatusCard title="Precisam de atenção" value={summary?.students_needing_attention ?? 0} detail="alertas explicáveis" state="warning" loading={loading} />
        <StatusCard title="Questões difíceis" value={summary?.difficult_questions ?? 0} detail="acerto abaixo de 40%" state="danger" loading={loading} />
        <StatusCard title="Correções pendentes" value={summary?.pending_manual_grading ?? 0} detail="respostas discursivas" state="neutral" loading={loading} />
      </div>

      <div className="analytics-two-columns">
        <article className="panel">
          <div className="panel-title-row"><div><h2>Turmas</h2><p>Abra uma turma para ver estudantes, tendências, BNCC e Pensamento Computacional.</p></div></div>
          <div className="analytics-link-list">
            {loading ? <LoadingState label="Carregando turmas" /> : classrooms.map((item) => <Link key={item.id} to={`/analytics/turmas/${item.id}`}><span><strong>{item.name}</strong><small>{item.grade || 'Ano não informado'}</small></span><b>Ver evolução →</b></Link>)}
            {!loading && !classrooms.length ? <EmptyState icon="activity" title="Nenhuma turma ativa" description="Ative uma turma para acompanhar sua evolução e seus indicadores pedagógicos." /> : null}
          </div>
        </article>
        <article className="panel">
          <div className="panel-title-row"><div><h2>Atividades recentes</h2><p>Analise questões, distratores, tempo e taxa de acerto.</p></div></div>
          <div className="analytics-link-list">
            {loading ? <LoadingState label="Carregando atividades" /> : assignments.slice(0, 8).map((item) => <Link key={item.id} to={`/analytics/atividades/${item.id}`}><span><strong>{item.title}</strong><small>{item.status}</small></span><b>Analisar →</b></Link>)}
            {!loading && !assignments.length ? <EmptyState icon="folder" title="Nenhuma publicação encontrada" description="Publique uma atividade para começar a reunir métricas de conclusão, tempo e desempenho." /> : null}
          </div>
        </article>
      </div>

      <div className="analytics-two-columns">
        <article className="panel">
          <div className="panel-title-row"><div><h2>Alertas pedagógicos</h2><p>Todos os alertas mostram a regra e as evidências utilizadas.</p></div><Link to="/analytics/alertas">Ver todos</Link></div>
          <div className="alert-stack">
            {loading ? <LoadingState label="Carregando alertas" rows={2} /> : alerts.map((alert) => <article className={`learning-alert severity-${alert.severity}`} key={alert.id}><div><span>{alert.severity}</span><h3>{alert.title}</h3><p>{alert.description}</p><small>{alert.explanation}</small></div></article>)}
            {!loading && !alerts.length ? <EmptyState icon="alert" title="Nenhum alerta aberto" description="Os indicadores atuais não geraram alertas pedagógicos que exigem atenção." /> : null}
          </div>
        </article>
        <article className="panel data-quality-panel">
          <h2>Qualidade dos dados</h2>
          {loading ? <LoadingState label="Carregando qualidade dos dados" rows={2} /> : quality ? <>
            <div className={`quality-status quality-${quality.status}`}>{quality.status === 'attention' ? 'Atenção' : 'Boa'}</div>
            <dl><div><dt>Tentativas válidas</dt><dd>{quality.valid_attempts}</dd></div><div><dt>Em andamento</dt><dd>{quality.incomplete_attempts}</dd></div><div><dt>Omissões</dt><dd>{quality.unanswered_items}</dd></div><div><dt>Correções manuais</dt><dd>{quality.manually_graded_answers}</dd></div></dl>
            {quality.notes.map((note) => <p className="quality-note" key={note}>{note}</p>)}
          </> : <EmptyState icon="alert" title="Qualidade indisponível" description="Atualize os indicadores para recalcular a qualidade das evidências." />}
        </article>
      </div>
    </section>
  )
}
