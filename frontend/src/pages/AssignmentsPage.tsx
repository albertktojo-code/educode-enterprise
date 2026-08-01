import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'
import type { AssignmentSummary, AssignmentType } from '../types/delivery'
import type { Classroom, DirectoryUser } from '../types/education'
import type { PedagogicalPackage } from '../types/studio'

const typeLabels: Record<AssignmentType, string> = {
  reading: 'Somente leitura',
  reading_exercise: 'HQ com exercícios',
  activity: 'Atividade',
  quiz: 'Quiz',
  assessment: 'Avaliação',
  pretest: 'Pré-teste',
  posttest: 'Pós-teste',
  reinforcement: 'Reforço',
  challenge: 'Desafio',
}

export function AssignmentsPage() {
  const [assignments, setAssignments] = useState<AssignmentSummary[]>([])
  const [packages, setPackages] = useState<PedagogicalPackage[]>([])
  const [classrooms, setClassrooms] = useState<Classroom[]>([])
  const [directory, setDirectory] = useState<DirectoryUser[]>([])
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({
    package_id: '', title: '', assignment_type: 'reading_exercise' as AssignmentType,
    instructions: '', classroom_id: '', user_id: '', due_at: '', maximum_attempts: 2,
    time_limit_minutes: 30, feedback_policy: 'after_submission', answer_key_policy: 'after_due_date',
  })

  async function load() {
    const [assignmentData, packageData, classroomData, userData] = await Promise.all([
      api<AssignmentSummary[]>('/delivery/assignments'),
      api<PedagogicalPackage[]>('/teacher-studio/packages'),
      api<Classroom[]>('/classrooms'),
      api<DirectoryUser[]>('/classrooms/directory'),
    ])
    setAssignments(assignmentData)
    setPackages(packageData)
    setClassrooms(classroomData)
    setDirectory(userData)
  }

  useEffect(() => { void load().catch((error: Error) => setMessage(error.message)) }, [])

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true); setMessage('')
    try {
      const recipients = []
      if (form.classroom_id) recipients.push({ recipient_type: 'classroom', classroom_id: form.classroom_id })
      if (form.user_id) recipients.push({ recipient_type: 'user', user_id: form.user_id })
      const created = await api<AssignmentSummary>('/delivery/assignments', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          due_at: form.due_at ? new Date(form.due_at).toISOString() : null,
          time_limit_minutes: form.time_limit_minutes || null,
          recipients,
          generate_mock_questions: form.assignment_type !== 'reading',
          show_result_immediately: form.feedback_policy === 'immediate',
          maximum_score: 10,
        }),
      })
      setMessage('Publicação criada como rascunho. Revise e publique quando estiver pronta.')
      setForm((current) => ({ ...current, title: '', package_id: '' }))
      setAssignments((current) => [created, ...current])
    } catch (error) { setMessage((error as Error).message) } finally { setBusy(false) }
  }

  return (
    <section>
      <header className="page-header"><div><span className="eyebrow">ENTREGA PEDAGÓGICA</span><h1>Publicações</h1><p>Envie materiais para turmas ou estudantes com prazo, tentativas e feedback controlado.</p></div></header>
      {message ? <div className="inline-message">{message}</div> : null}
      <div className="delivery-layout">
        <form className="panel form-grid" onSubmit={submit}>
          <h2>Nova publicação</h2>
          <label>Pacote pedagógico<select required value={form.package_id} onChange={(event: { target: { value: string } }) => {
            const pkg = packages.find((item) => item.id === event.target.value)
            setForm({ ...form, package_id: event.target.value, title: form.title || pkg?.title || '' })
          }}><option value="">Selecione</option>{packages.map((pkg) => <option key={pkg.id} value={pkg.id}>{pkg.title}</option>)}</select></label>
          <label>Título<input required value={form.title} onChange={(event: { target: { value: string } }) => setForm({ ...form, title: event.target.value })} /></label>
          <label>Tipo<select value={form.assignment_type} onChange={(event: { target: { value: string } }) => setForm({ ...form, assignment_type: event.target.value as AssignmentType })}>{Object.entries(typeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <label>Turma<select value={form.classroom_id} onChange={(event: { target: { value: string } }) => setForm({ ...form, classroom_id: event.target.value })}><option value="">Nenhuma</option>{classrooms.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label>Estudante específico<select value={form.user_id} onChange={(event: { target: { value: string } }) => setForm({ ...form, user_id: event.target.value })}><option value="">Nenhum</option>{directory.filter((item) => item.organization_role === 'member').map((item) => <option key={item.id} value={item.id}>{item.full_name}</option>)}</select></label>
          <label>Prazo<input type="datetime-local" value={form.due_at} onChange={(event: { target: { value: string } }) => setForm({ ...form, due_at: event.target.value })} /></label>
          <label>Tentativas<input type="number" min={1} max={20} value={form.maximum_attempts} onChange={(event: { target: { value: string } }) => setForm({ ...form, maximum_attempts: Number(event.target.value) })} /></label>
          <label>Tempo (min)<input type="number" min={1} value={form.time_limit_minutes} onChange={(event: { target: { value: string } }) => setForm({ ...form, time_limit_minutes: Number(event.target.value) })} /></label>
          <label>Feedback<select value={form.feedback_policy} onChange={(event: { target: { value: string } }) => setForm({ ...form, feedback_policy: event.target.value })}><option value="immediate">Imediato</option><option value="after_submission">Após a entrega</option><option value="after_due_date">Após o prazo</option><option value="manual_release">Liberação manual</option></select></label>
          <label>Gabarito<select value={form.answer_key_policy} onChange={(event: { target: { value: string } }) => setForm({ ...form, answer_key_policy: event.target.value })}><option value="never">Nunca</option><option value="after_submission">Após a entrega</option><option value="after_due_date">Após o prazo</option><option value="manual_release">Liberação manual</option></select></label>
          <label className="span-2">Orientações<textarea rows={4} value={form.instructions} onChange={(event: { target: { value: string } }) => setForm({ ...form, instructions: event.target.value })} /></label>
          <button className="primary" disabled={busy}>{busy ? 'Criando...' : 'Criar rascunho'}</button>
        </form>

        <div className="panel"><div className="panel-title-row"><h2>Minhas publicações</h2><span>{assignments.length}</span></div><div className="assignment-list">
          {assignments.map((item) => <article className="assignment-card" key={item.id}><div><span className={`status-chip status-${item.status}`}>{item.status}</span><h3>{item.title}</h3><p>{typeLabels[item.assignment_type]}</p></div><div className="assignment-meta"><span>{item.due_at ? `Prazo: ${new Date(item.due_at).toLocaleString('pt-BR')}` : 'Sem prazo'}</span><span>{item.maximum_attempts} tentativa(s)</span></div><Link to={`/publicacoes/${item.id}`}>Abrir e acompanhar</Link></article>)}
          {!assignments.length ? <p className="muted">Nenhuma publicação criada.</p> : null}
        </div></div>
      </div>
    </section>
  )
}
