import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../lib/api'
import type { AttemptPolicy, ClassroomAnalytics } from '../types/analytics'

const trendIcon = { up: '↗', down: '↘', stable: '→' }

export function ClassroomAnalyticsPage() {
  const { classroomId = '' } = useParams()
  const [data, setData] = useState<ClassroomAnalytics | null>(null)
  const [policy, setPolicy] = useState<AttemptPolicy>('best')
  const [message, setMessage] = useState('')

  async function load(nextPolicy: AttemptPolicy = policy) {
    setData(await api<ClassroomAnalytics>(`/analytics/classrooms/${classroomId}?attempt_policy=${nextPolicy}`))
  }
  useEffect(() => { void load().catch((error: Error) => setMessage(error.message)) }, [classroomId])

  return <section>
    <header className="page-header"><div><span className="eyebrow">ANÁLISE DA TURMA</span><h1>{data?.classroom_name ?? 'Turma'}</h1><p>Resultados agregados com acesso ao histórico individual.</p></div><label>Considerar<select value={policy} onChange={(event) => { const next = event.target.value as AttemptPolicy; setPolicy(next); void load(next) }}><option value="best">Melhor tentativa</option><option value="first">Primeira tentativa</option><option value="latest">Última tentativa</option><option value="all">Todas</option></select></label></header>
    {message ? <div className="inline-message">{message}</div> : null}
    <div className="analytics-card-grid compact"><article className="metric-card"><span>Estudantes</span><strong>{data?.student_count ?? 0}</strong></article><article className="metric-card"><span>Média</span><strong>{data?.average_percentage?.toFixed(1) ?? '—'}%</strong></article><article className="metric-card"><span>Mediana</span><strong>{data?.median_percentage?.toFixed(1) ?? '—'}%</strong></article><article className="metric-card"><span>Conclusão</span><strong>{data?.completion_rate.toFixed(1) ?? '0'}%</strong></article></div>
    <div className="analytics-two-columns">
      <article className="panel"><h2>Desempenho por habilidade e PC</h2><div className="skill-list">{data?.skills.map((skill) => { const name = skill.skill_code || skill.ct_pillar_code; return <div key={`${skill.skill_code}-${skill.ct_pillar_code}`}><span><strong>{name}</strong><small>{skill.evidence_count} evidências · confiança {skill.confidence_score.toFixed(0)}%</small></span><div className="progress-track"><i style={{ width: `${skill.proficiency_score}%` }} /></div><b>{skill.proficiency_score.toFixed(1)}%</b></div> })}{!data?.skills.length ? <p className="muted">Atualize os indicadores para visualizar habilidades.</p> : null}</div></article>
      <article className="panel"><h2>Evolução por atividade</h2><div className="trend-bars">{data?.trend.map((point) => <div key={point.label}><span>{point.label}</span><div><i style={{ width: `${point.value}%` }} /></div><b>{point.value.toFixed(1)}%</b></div>)}</div></article>
    </div>
    <article className="panel"><h2>Estudantes</h2><div className="analytics-table"><div className="analytics-table-head"><span>Estudante</span><span>Média</span><span>Atividades</span><span>Tendência</span><span>Ação</span></div>{data?.students.map((student) => <div className={`analytics-table-row attention-${student.attention_level}`} key={student.student_id}><span><strong>{student.student_name}</strong></span><span>{student.average_percentage === null ? 'Sem dados' : `${student.average_percentage.toFixed(1)}%`}</span><span>{student.assignments_completed}</span><span className={`trend-${student.trend_direction}`}>{trendIcon[student.trend_direction]} {student.trend_direction}</span><span><Link to={`/analytics/estudantes/${student.student_id}`}>Abrir histórico</Link></span></div>)}</div></article>
  </section>
}
