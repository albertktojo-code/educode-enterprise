import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { api } from '../lib/api'
import type { AttemptResult, AttemptWorkspace, StudentAssignmentDetail, StudentQuestion } from '../types/delivery'

type AnswerMap = Record<string, Record<string, unknown>>

function safeAnimeReturnPath(value: string | null): string | null {
  if (!value) return null
  try {
    const base = 'https://educode.local'
    const parsed = new URL(value, base)
    if (parsed.origin !== base || parsed.pathname !== '/anime-library') return null
    return `${parsed.pathname}${parsed.search}`
  } catch {
    return null
  }
}

export function StudentAssignmentPage() {
  const { assignmentId } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const returnPath = safeAnimeReturnPath(searchParams.get('returnTo'))
  const [detail, setDetail] = useState<StudentAssignmentDetail | null>(null)
  const [workspace, setWorkspace] = useState<AttemptWorkspace | null>(null)
  const [answers, setAnswers] = useState<AnswerMap>({})
  const [result, setResult] = useState<AttemptResult | null>(null)
  const [pageIndex, setPageIndex] = useState(0)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    if (!assignmentId) return
    const data = await api<StudentAssignmentDetail>(`/student/assignments/${assignmentId}`)
    setDetail(data)
    if (data.active_attempt_id) {
      const active = await api<AttemptWorkspace>(`/student/attempts/${data.active_attempt_id}`)
      setWorkspace(active)
      setAnswers(Object.fromEntries(active.attempt.answers.map((item) => [item.question_id, item.answer_payload])))
    }
  }
  useEffect(() => { void load().catch((error: Error) => setMessage(error.message)) }, [assignmentId])

  const comicPages = useMemo(() => {
    const comic = detail?.material.comic as { pages?: Array<Record<string, unknown>> } | undefined
    return comic?.pages ?? []
  }, [detail])

  async function start() {
    if (!assignmentId) return
    setBusy(true)
    try {
      const data = await api<AttemptWorkspace>(`/student/assignments/${assignmentId}/attempts`, { method: 'POST', body: JSON.stringify({ preview_mode: false }) })
      setWorkspace(data); setAnswers(Object.fromEntries(data.attempt.answers.map((item) => [item.question_id, item.answer_payload])))
    } catch (error) { setMessage((error as Error).message) } finally { setBusy(false) }
  }

  function payloadFor(question: StudentQuestion, value: string | boolean | string[]) {
    if (question.question_type === 'multiple_choice') return { selected_option_id: value }
    if (question.question_type === 'true_false') return { value }
    if (question.question_type === 'multiple_select') return { selected_option_ids: value }
    if (question.question_type === 'numeric') return { value }
    return { text: value }
  }

  async function save(question: StudentQuestion, payload: Record<string, unknown>) {
    if (!workspace) return
    setAnswers((current) => ({ ...current, [question.id]: payload }))
    try {
      const response = await api<{ autosave_revision: number; feedback_available: boolean; feedback?: string | null }>(`/student/attempts/${workspace.attempt.id}/answers/${question.id}`, { method: 'PUT', body: JSON.stringify({ answer_payload: payload, expected_revision: workspace.attempt.autosave_revision }) })
      setWorkspace((current) => current ? { ...current, attempt: { ...current.attempt, autosave_revision: response.autosave_revision } } : current)
      if (response.feedback_available && response.feedback) setMessage(response.feedback)
    } catch (error) { setMessage((error as Error).message) }
  }

  async function submit() {
    if (!workspace || !window.confirm('Enviar esta tentativa?')) return
    setBusy(true)
    try {
      await api(`/student/attempts/${workspace.attempt.id}/submit`, { method: 'POST', body: JSON.stringify({ confirm_submission: true, time_spent_seconds: 0 }) })
      const resultData = await api<AttemptResult>(`/student/attempts/${workspace.attempt.id}/result`)
      setResult(resultData); setMessage(returnPath ? 'Atividade entregue. Retornando ao vídeo…' : resultData.result_available ? 'Atividade entregue.' : 'Atividade entregue. O resultado será liberado depois.')
      if (returnPath) navigate(returnPath, { replace: true })
    } catch (error) { setMessage((error as Error).message) } finally { setBusy(false) }
  }

  if (!detail) return <section><p>{message || 'Carregando atividade...'}</p></section>
  return <section className="student-activity-page"><header className="page-header"><div><Link to={returnPath ?? '/aluno/atividades'}>{returnPath ? '← Voltar ao vídeo' : '← Minhas atividades'}</Link><h1>{detail.title}</h1><p>{detail.instructions}</p></div><div className="student-deadline"><span>Prazo</span><strong>{detail.due_at ? new Date(detail.due_at).toLocaleString('pt-BR') : 'Livre'}</strong></div></header>{message ? <div className="inline-message">{message}</div> : null}
    <div className="student-activity-layout"><div className="panel material-reader"><div className="panel-title-row"><h2>Material</h2><span>{comicPages.length ? `Página ${pageIndex + 1} de ${comicPages.length}` : 'Conteúdo de estudo'}</span></div>{comicPages.length ? <><article className="comic-reader-page">{(() => { const page = comicPages[pageIndex] as { title?: string; panels?: Array<{ id?: string; scene_description?: string; alt_text?: string; balloons?: Array<{ id?: string; speaker?: string; text?: string }> }> }; return <><h3>{page.title || `Página ${pageIndex + 1}`}</h3><div className="comic-reader-panels">{page.panels?.map((panel, index) => <div className="comic-reader-panel" key={panel.id ?? index}><p>{panel.scene_description || panel.alt_text}</p>{panel.balloons?.map((balloon, balloonIndex) => <blockquote key={balloon.id ?? balloonIndex}><strong>{balloon.speaker}</strong>{balloon.text}</blockquote>)}</div>)}</div></> })()}</article><div className="reader-controls"><button disabled={pageIndex === 0} onClick={() => setPageIndex((value) => value - 1)}>Anterior</button><button disabled={pageIndex >= comicPages.length - 1} onClick={() => setPageIndex((value) => value + 1)}>Próxima</button></div></> : <pre className="material-json">{JSON.stringify(detail.material.student_materials ?? detail.material, null, 2)}</pre>}</div>
    <aside className="panel activity-workspace"><h2>Exercícios</h2>{!workspace && !result ? <div className="start-activity"><p>{detail.maximum_attempts - detail.attempts_used} tentativa(s) restante(s).</p><button className="primary" disabled={!detail.can_start || busy} onClick={() => void start()}>{busy ? 'Abrindo...' : 'Iniciar atividade'}</button></div> : null}{workspace && !result ? <>{workspace.questions.map((question) => <article className="student-question" key={question.id}><span>Questão {question.position} · {question.points} ponto(s)</span><h3>{question.prompt}</h3>{question.question_type === 'multiple_choice' ? question.options.map((option) => <label className="answer-option" key={String(option.id)}><input type="radio" name={question.id} checked={answers[question.id]?.selected_option_id === option.id} onChange={() => void save(question, payloadFor(question, String(option.id)))} />{option.text}</label>) : question.question_type === 'true_false' ? <div className="boolean-options"><button onClick={() => void save(question, payloadFor(question, true))}>Verdadeiro</button><button onClick={() => void save(question, payloadFor(question, false))}>Falso</button></div> : <textarea value={String(answers[question.id]?.text ?? answers[question.id]?.value ?? '')} onChange={(event: { target: { value: string } }) => setAnswers((current) => ({ ...current, [question.id]: payloadFor(question, event.target.value) }))} onBlur={() => void save(question, answers[question.id] ?? {})} />}</article>)}<button className="primary submit-attempt" disabled={busy} onClick={() => void submit()}>Entregar atividade</button></> : null}{result ? <div className="result-card"><h3>{result.result_available ? `Resultado: ${result.percentage}%` : 'Entrega registrada'}</h3><p>{result.grading_complete ? 'Correção concluída.' : 'Há respostas aguardando correção do professor.'}</p>{result.answers.map((item) => <article key={item.question_id}><strong>{item.prompt}</strong><span>{item.awarded_score} ponto(s)</span><p>{item.feedback}</p></article>)}{returnPath ? <Link to={returnPath}>Retornar ao vídeo</Link> : null}</div> : null}</aside></div>
  </section>
}
