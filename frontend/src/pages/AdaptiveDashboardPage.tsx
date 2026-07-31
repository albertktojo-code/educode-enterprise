import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { EmptyState } from '../components/EmptyState'
import { LoadingState } from '../components/LoadingState'
import { StatusCard } from '../components/StatusCard'
import { api } from '../lib/api'
import type { AdaptiveDashboard } from '../types/adaptive'

const statusLabels: Record<string, string> = {
  pending_review: 'Aguardando revisão',
  approved: 'Aprovada',
  rejected: 'Rejeitada',
  changes_requested: 'Alterações solicitadas',
}

export function AdaptiveDashboardPage() {
  const [dashboard, setDashboard] = useState<AdaptiveDashboard | null>(null)
  const [students, setStudents] = useState<Array<{ id: string; full_name: string; email: string; is_active: boolean }>>([])
  const [studentId, setStudentId] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    try {
      const [summary, users] = await Promise.all([
        api<AdaptiveDashboard>('/adaptive/dashboard'),
        api<Array<{ id: string; full_name: string; email: string; is_active: boolean }>>('/adaptive/students'),
      ])
      setDashboard(summary)
      const studentUsers = users.filter((item) => item.is_active)
      setStudents(studentUsers)
      setStudentId((current) => current || studentUsers[0]?.id || '')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load().catch((error: Error) => setMessage(error.message)) }, [])

  const masteryTotal = useMemo(
    () => Object.values(dashboard?.mastery_distribution ?? {}).reduce((sum, value) => sum + value, 0),
    [dashboard],
  )

  async function refreshStudent() {
    if (!studentId) return
    setBusy(true); setMessage('')
    try {
      const result = await api<{ skill_states_updated: number; recommendations_created: number }>('/adaptive/refresh', {
        method: 'POST',
        body: JSON.stringify({ student_id: studentId, generate_recommendations: true, include_spaced_review: true }),
      })
      setMessage(`${result.skill_states_updated} estados atualizados e ${result.recommendations_created} recomendações criadas.`)
      await load()
    } catch (error) { setMessage((error as Error).message) } finally { setBusy(false) }
  }

  return (
    <section>
      <header className="page-header adaptive-header">
        <div>
          <span className="eyebrow">SPRINT 14 — APRENDIZAGEM ADAPTATIVA</span>
          <h1>Trilhas personalizadas</h1>
          <p>Transforme evidências de exercícios e avaliações em recomendações explicáveis, sempre revisadas pelo professor.</p>
        </div>
        <div className="adaptive-toolbar">
          <select aria-label="Selecionar estudante" value={studentId} onChange={(event: { target: { value: string } }) => setStudentId(event.target.value)}>
            {!students.length ? <option value="">Nenhum estudante ativo</option> : null}
            {students.map((student) => <option key={student.id} value={student.id}>{student.full_name}</option>)}
          </select>
          <Link className="secondary-button" to="/ia?module=adaptive&action=generate_learning_material">Criar material com IA</Link>
          <button className="primary-button" disabled={!studentId || busy} onClick={() => void refreshStudent()} type="button">
            {busy ? 'Calculando...' : 'Atualizar e recomendar'}
          </button>
        </div>
      </header>

      {message ? <div className="inline-message" role="status">{message}</div> : null}

      <div className="data-metric-grid data-metric-grid--six" aria-label="Indicadores adaptativos">
        <StatusCard title="Estudantes com perfil" value={dashboard?.students_with_profiles ?? 0} detail="mapas de domínio ativos" state="info" loading={loading} />
        <StatusCard title="Trilhas ativas" value={dashboard?.active_paths ?? 0} detail="individuais ou por grupo" state="success" loading={loading} />
        <StatusCard title="Aguardando revisão" value={dashboard?.pending_recommendations ?? 0} detail="decisão obrigatória do professor" state="warning" loading={loading} />
        <StatusCard title="Revisões programadas" value={dashboard?.scheduled_reviews ?? 0} detail="prática espaçada" state="neutral" loading={loading} />
        <StatusCard title="Baixa confiança" value={dashboard?.low_confidence_states ?? 0} detail="precisam de mais evidências" state="warning" loading={loading} />
        <StatusCard title="Dimensões prioritárias" value={dashboard?.dimensions_needing_attention ?? 0} detail="domínio abaixo de 65%" state="danger" loading={loading} />
      </div>

      <div className="adaptive-nav-grid">
        <Link className="adaptive-nav-card" to="/adaptativo/recomendacoes"><strong>Revisar recomendações</strong><span>Aceitar, editar, rejeitar ou converter em trilha.</span></Link>
        <Link className="adaptive-nav-card" to="/adaptativo/trilhas"><strong>Gerenciar trilhas</strong><span>Acompanhar etapas, critérios de avanço e resultados.</span></Link>
        {studentId ? <Link className="adaptive-nav-card" to={`/adaptativo/estudantes/${studentId}`}><strong>Abrir perfil selecionado</strong><span>Mapa de domínio, confiança, tendências e evidências.</span></Link> : null}
      </div>

      <div className="analytics-two-columns">
        <article className="panel">
          <div className="panel-heading"><div><h2>Recomendações recentes</h2><p>Nenhuma recomendação é enviada automaticamente ao estudante.</p></div><Link to="/adaptativo/recomendacoes">Ver todas</Link></div>
          <div className="adaptive-list">
            {loading ? <LoadingState label="Carregando recomendações" /> : dashboard?.recent_recommendations.map((item) => (
              <article key={item.id}>
                <div><span className={`status-pill status-${item.status}`}>{statusLabels[item.status] ?? item.status}</span><h3>{item.title}</h3><p>{item.rationale}</p></div>
                {item.student_id ? <Link to={`/adaptativo/estudantes/${item.student_id}`}>Ver estudante →</Link> : null}
              </article>
            ))}
            {!loading && !dashboard?.recent_recommendations.length ? <EmptyState icon="activity" title="Nenhuma recomendação recente" description="Atualize um estudante para gerar sugestões explicáveis que aguardam revisão docente." /> : null}
          </div>
        </article>

        <article className="panel">
          <h2>Distribuição de domínio</h2>
          <p>O nível sempre considera quantidade e consistência das evidências.</p>
          <div className="mastery-distribution">
            {loading ? <LoadingState label="Carregando distribuição de domínio" rows={4} /> : Object.entries(dashboard?.mastery_distribution ?? {}).map(([level, count]) => (
              <div key={level}><div><span>{level.replaceAll('_', ' ')}</span><strong>{count}</strong></div><div className="mastery-track"><span style={{ width: `${masteryTotal ? (count / masteryTotal) * 100 : 0}%` }} /></div></div>
            ))}
            {!loading && !masteryTotal ? <EmptyState icon="activity" title="Domínio ainda não calculado" description="Novas evidências alimentarão a distribuição após a atualização do estudante." /> : null}
          </div>
          <div className="privacy-note"><strong>Proteção pedagógica:</strong> não há ranking público, rótulos permanentes ou limitação automática de acesso.</div>
        </article>
      </div>
    </section>
  )
}
