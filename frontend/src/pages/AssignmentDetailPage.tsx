import { FormEvent, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../lib/api'
import type { AssignmentDetail, AssignmentProgress, GradingQueueItem, StudentPreview } from '../types/delivery'

export function AssignmentDetailPage() {
  const { assignmentId } = useParams()
  const [assignment, setAssignment] = useState<AssignmentDetail | null>(null)
  const [progress, setProgress] = useState<AssignmentProgress | null>(null)
  const [queue, setQueue] = useState<GradingQueueItem[]>([])
  const [message, setMessage] = useState('')
  const [preview, setPreview] = useState<StudentPreview | null>(null)
  const [grade, setGrade] = useState({ answerId: '', score: 0, feedback: '' })

  async function load() {
    if (!assignmentId) return
    const [detail, report, grading] = await Promise.all([
      api<AssignmentDetail>(`/delivery/assignments/${assignmentId}`),
      api<AssignmentProgress>(`/delivery/assignments/${assignmentId}/progress`),
      api<GradingQueueItem[]>(`/delivery/assignments/${assignmentId}/grading-queue`),
    ])
    setAssignment(detail); setProgress(report); setQueue(grading)
  }
  useEffect(() => { void load().catch((error: Error) => setMessage(error.message)) }, [assignmentId])

  async function action(path: string) {
    try { await api(path, { method: 'POST' }); await load(); setMessage('Operação concluída.') }
    catch (error) { setMessage((error as Error).message) }
  }

  async function openPreview() {
    try { setPreview(await api<StudentPreview>(`/delivery/assignments/${assignmentId}/preview`)) }
    catch (error) { setMessage((error as Error).message) }
  }

  async function grantAttempt(studentId: string) {
    try {
      await api(`/delivery/assignments/${assignmentId}/students/${studentId}/grant-attempt`, {
        method: 'POST',
        body: JSON.stringify({ additional_attempts: 1, reason: 'Tentativa adicional liberada pelo professor' }),
      })
      await load(); setMessage('Tentativa adicional liberada.')
    } catch (error) { setMessage((error as Error).message) }
  }

  async function duplicate() {
    try {
      const copy = await api<AssignmentDetail>(`/delivery/assignments/${assignmentId}/duplicate`, { method: 'POST', body: JSON.stringify({ copy_recipients: true }) })
      setMessage(`Cópia criada: ${copy.title}`)
    } catch (error) { setMessage((error as Error).message) }
  }

  async function submitGrade(event: FormEvent) {
    event.preventDefault()
    try {
      await api(`/delivery/answers/${grade.answerId}/grade`, { method: 'PATCH', body: JSON.stringify({ awarded_score: grade.score, teacher_feedback: grade.feedback }) })
      setGrade({ answerId: '', score: 0, feedback: '' }); await load(); setMessage('Resposta corrigida.')
    } catch (error) { setMessage((error as Error).message) }
  }

  if (!assignment || !progress) return <section><p>{message || 'Carregando publicação...'}</p></section>
  return <section>
    <header className="page-header"><div><span className="eyebrow">ACOMPANHAMENTO</span><h1>{assignment.title}</h1><p>Snapshot v{assignment.snapshot_version} · {assignment.questions.length} questão(ões)</p></div><div className="header-actions"><Link to="/publicacoes">Voltar</Link><button onClick={() => void openPreview()}>Visualizar como estudante</button><button onClick={() => void duplicate()}>Duplicar</button>{assignment.status === 'draft' || assignment.status === 'scheduled' ? <button className="primary" onClick={() => void action(`/delivery/assignments/${assignment.id}/publish`)}>Publicar</button> : null}{assignment.status === 'published' ? <button onClick={() => void action(`/delivery/assignments/${assignment.id}/close`)}>Encerrar</button> : null}<button onClick={() => void action(`/delivery/assignments/${assignment.id}/release-results`)}>Liberar resultados</button></div></header>
    {message ? <div className="inline-message">{message}</div> : null}
    <div className="metric-grid"><article><span>Estudantes</span><strong>{progress.total_students}</strong></article><article><span>Entregues/corrigidos</span><strong>{progress.submitted + progress.graded}</strong></article><article><span>Conclusão</span><strong>{progress.completion_rate}%</strong></article><article><span>Média</span><strong>{progress.average_percentage ?? '—'}%</strong></article></div>
    <div className="delivery-layout"><div className="panel"><h2>Progresso por estudante</h2><div className="table-wrap"><table><thead><tr><th>Estudante</th><th>Status</th><th>Tentativas</th><th>Melhor resultado</th><th>Última atividade</th><th>Ações</th></tr></thead><tbody>{progress.students.map((student) => <tr key={student.student_id}><td>{student.student_name}<small>{student.student_email}</small></td><td>{student.progress_status}</td><td>{student.attempts_count}</td><td>{student.best_percentage ?? '—'}%</td><td>{student.last_activity_at ? new Date(student.last_activity_at).toLocaleString('pt-BR') : '—'}</td><td><button onClick={() => void grantAttempt(student.student_id)}>+ tentativa</button></td></tr>)}</tbody></table></div></div>
    <div className="panel"><h2>Análise básica das questões</h2>{progress.questions.map((question) => <article className="question-stat" key={question.question_id}><strong>Q{question.position}. {question.prompt}</strong><span>{question.response_count} resposta(s) · {question.correct_rate ?? '—'}% de acertos</span></article>)}</div></div>
    {preview ? <section className="panel student-preview-panel"><div className="panel-title-row"><h2>Prévia como estudante</h2><button onClick={() => setPreview(null)}>Fechar</button></div><p>{preview.assignment.instructions}</p><strong>{preview.questions.length} questão(ões)</strong><pre>{JSON.stringify(preview.assignment.material, null, 2)}</pre></section> : null}
    <section className="panel"><h2>Correções manuais pendentes ({queue.length})</h2>{queue.map((item) => <article className="grading-card" key={item.answer_id}><strong>{item.student_name}</strong><p>{item.question_prompt}</p><pre>{JSON.stringify(item.answer_payload, null, 2)}</pre><button onClick={() => setGrade({ answerId: item.answer_id, score: item.awarded_score, feedback: item.teacher_feedback ?? '' })}>Corrigir</button></article>)}{grade.answerId ? <form className="inline-grade-form" onSubmit={submitGrade}><label>Nota<input type="number" min={0} step="0.1" value={grade.score} onChange={(event: { target: { value: string } }) => setGrade({ ...grade, score: Number(event.target.value) })} /></label><label>Feedback<textarea value={grade.feedback} onChange={(event: { target: { value: string } }) => setGrade({ ...grade, feedback: event.target.value })} /></label><button className="primary">Salvar correção</button></form> : null}</section>
  </section>
}
