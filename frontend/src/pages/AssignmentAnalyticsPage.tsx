import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { api } from '../lib/api'
import type { AssignmentAnalytics } from '../types/analytics'

export function AssignmentAnalyticsPage() {
  const { assignmentId = '' } = useParams()
  const [data, setData] = useState<AssignmentAnalytics | null>(null)
  const [message, setMessage] = useState('')
  useEffect(() => { void api<AssignmentAnalytics>(`/analytics/assignments/${assignmentId}`).then(setData).catch((error: Error) => setMessage(error.message)) }, [assignmentId])
  return <section>
    <header className="page-header"><div><span className="eyebrow">ANÁLISE DA ATIVIDADE</span><h1>{data?.assignment_title ?? 'Atividade'}</h1><p>Taxa de acerto, dificuldade, distratores e qualidade dos dados.</p></div></header>
    {message ? <div className="inline-message">{message}</div> : null}
    <div className="analytics-card-grid compact"><article className="metric-card"><span>Participantes</span><strong>{data?.participant_count ?? 0}</strong></article><article className="metric-card"><span>Conclusão</span><strong>{data?.completion_rate.toFixed(1) ?? '0'}%</strong></article><article className="metric-card"><span>Média</span><strong>{data?.average_percentage?.toFixed(1) ?? '—'}%</strong></article><article className="metric-card"><span>Tempo médio</span><strong>{data?.average_time_seconds ? `${Math.round(data.average_time_seconds / 60)} min` : '—'}</strong></article></div>
    {data?.data_quality_notes.map((note) => <div className="quality-note" key={note}>{note}</div>)}
    <div className="question-analytics-list">{data?.questions.map((question) => <article className="panel question-analytics" key={question.question_id}><div className="question-title"><div><span>Questão {question.position}</span><h2>{question.prompt}</h2></div><div className={`difficulty difficulty-${question.difficulty_label}`}>{question.difficulty_label}</div></div><div className="question-metrics"><span><b>{question.correct_rate?.toFixed(1) ?? '—'}%</b> acertos</span><span><b>{question.response_count}</b> respostas</span><span><b>{question.average_response_time ? `${Math.round(question.average_response_time)}s` : '—'}</b> tempo médio</span><span><b>{question.discrimination_index?.toFixed(2) ?? '—'}</b> discriminação</span></div><div className="distractor-list">{question.distractors.map((item) => <div className={item.is_correct_option ? 'correct-distractor' : ''} key={item.answer}><span>{item.answer}</span><div><i style={{ width: `${item.percentage}%` }} /></div><b>{item.percentage.toFixed(1)}%</b></div>)}</div><footer>{[...question.curriculum_skill_codes, ...question.ct_pillar_codes].map((code) => <span className="tag" key={code}>{code}</span>)}</footer></article>)}</div>
  </section>
}
