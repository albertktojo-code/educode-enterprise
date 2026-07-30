import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { api } from '../lib/api'
import type { StudentAnalytics } from '../types/analytics'

export function StudentAnalyticsPage() {
  const { studentId = '' } = useParams()
  const [data, setData] = useState<StudentAnalytics | null>(null)
  const [message, setMessage] = useState('')
  useEffect(() => { void api<StudentAnalytics>(`/analytics/students/${studentId}`).then(setData).catch((error: Error) => setMessage(error.message)) }, [studentId])
  return <section>
    <header className="page-header"><div><span className="eyebrow">EVOLUÇÃO INDIVIDUAL</span><h1>{data?.student_name ?? 'Estudante'}</h1><p>{data?.student_email}</p></div></header>
    {message ? <div className="inline-message">{message}</div> : null}
    <div className="analytics-card-grid compact"><article className="metric-card"><span>Média</span><strong>{data?.average_percentage?.toFixed(1) ?? '—'}%</strong></article><article className="metric-card"><span>Atividades</span><strong>{data?.activities_completed ?? 0}</strong></article><article className="metric-card"><span>Tentativas</span><strong>{data?.total_attempts ?? 0}</strong></article><article className="metric-card"><span>Tempo médio</span><strong>{data?.average_time_seconds ? `${Math.round(data.average_time_seconds / 60)} min` : '—'}</strong></article></div>
    <div className="analytics-two-columns"><article className="panel"><h2>Habilidades</h2><div className="skill-list">{data?.skills.map((skill) => <div key={`${skill.skill_code}-${skill.ct_pillar_code}`}><span><strong>{skill.skill_code || skill.ct_pillar_code}</strong><small>{skill.mastery_level} · {skill.evidence_count} evidências</small></span><div className="progress-track"><i style={{ width: `${skill.proficiency_score}%` }} /></div><b>{skill.proficiency_score.toFixed(1)}%</b></div>)}</div></article><article className="panel"><h2>Próximos passos</h2><div className="recommendation-list">{data?.recommendations.map((item) => <p key={item}>{item}</p>)}</div></article></div>
    <article className="panel"><h2>Histórico de atividades</h2><div className="analytics-table"><div className="analytics-table-head"><span>Atividade</span><span>Tentativa</span><span>Resultado</span><span>Tempo</span><span>Data</span></div>{data?.activities.map((item) => <div className="analytics-table-row" key={`${item.assignment_id}-${item.attempt_number}`}><span>{item.assignment_title}</span><span>{item.attempt_number}</span><span>{item.percentage.toFixed(1)}%</span><span>{Math.round(item.time_spent_seconds / 60)} min</span><span>{item.submitted_at ? new Date(item.submitted_at).toLocaleDateString('pt-BR') : '—'}</span></div>)}</div></article>
  </section>
}
