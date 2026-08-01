import { useEffect, useState } from 'react'

import { api } from '../lib/api'
import type { StudentOwnProgress } from '../types/analytics'

export function StudentProgressPage() {
  const [data, setData] = useState<StudentOwnProgress | null>(null)
  const [message, setMessage] = useState('')
  useEffect(() => { void api<StudentOwnProgress>('/analytics/student/progress').then(setData).catch((error: Error) => setMessage(error.message)) }, [])
  return <section><header className="page-header student-progress-header"><div><span className="eyebrow">MEU PROGRESSO</span><h1>Sua evolução</h1><p>Acompanhe conquistas e próximos desafios sem comparação com outros estudantes.</p></div></header>{message ? <div className="inline-message">{message}</div> : null}<div className="analytics-card-grid compact"><article className="metric-card"><span>Média</span><strong>{data?.average_percentage?.toFixed(1) ?? '—'}%</strong></article><article className="metric-card"><span>Atividades concluídas</span><strong>{data?.completed_activities ?? 0}</strong></article></div><div className="analytics-two-columns"><article className="panel"><h2>Seus pontos fortes</h2><div className="skill-list">{data?.strengths.map((item) => <div key={`${item.skill_code}-${item.ct_pillar_code}`}><span><strong>{item.skill_code || item.ct_pillar_code}</strong><small>{item.evidence_count} evidências</small></span><div className="progress-track"><i style={{ width: `${item.proficiency_score}%` }} /></div><b>{item.proficiency_score.toFixed(0)}%</b></div>)}{!data?.strengths.length ? <p className="muted">Continue realizando atividades para reunir novas evidências.</p> : null}</div></article><article className="panel"><h2>Próximos desafios</h2><div className="recommendation-list">{data?.next_steps.map((item) => <p key={item}>{item}</p>)}</div></article></div></section>
}
