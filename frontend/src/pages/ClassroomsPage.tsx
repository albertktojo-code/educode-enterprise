import { FormEvent, useEffect, useMemo, useState } from 'react'

import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import type {
  Classroom,
  DirectoryUser,
  Enrollment,
  EnrollmentRole,
  Subject,
} from '../types/education'

const emptyForm = {
  name: '',
  grade: '',
  school_year: new Date().getFullYear(),
  subject_id: '',
  description: '',
}

const enrollmentLabels: Record<EnrollmentRole, string> = {
  student: 'Estudante',
  teacher: 'Professor',
  assistant: 'Assistente',
}

export function ClassroomsPage() {
  const { user } = useAuth()
  const role = user?.memberships[0]?.role
  const canWrite = ['owner', 'admin', 'teacher'].includes(role ?? '')
  const [classrooms, setClassrooms] = useState<Classroom[]>([])
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [directory, setDirectory] = useState<DirectoryUser[]>([])
  const [participants, setParticipants] = useState<Enrollment[]>([])
  const [selectedClassroom, setSelectedClassroom] = useState<Classroom | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'active' | 'inactive'>('all')
  const [form, setForm] = useState(emptyForm)
  const [participantForm, setParticipantForm] = useState({
    user_id: '',
    role: 'student' as EnrollmentRole,
  })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function load() {
    try {
      const requests: [Promise<Classroom[]>, Promise<Subject[]>, Promise<DirectoryUser[]>?] = [
        api<Classroom[]>('/classrooms'),
        api<Subject[]>('/subjects'),
      ]
      if (canWrite) requests.push(api<DirectoryUser[]>('/classrooms/directory'))
      const [classroomData, subjectData, directoryData = []] = await Promise.all(requests)
      setClassrooms(classroomData)
      setSubjects(subjectData)
      setDirectory(directoryData)
      if (selectedClassroom) {
        const updated = classroomData.find((item) => item.id === selectedClassroom.id) ?? null
        setSelectedClassroom(updated)
      }
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao carregar turmas.')
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const visibleClassrooms = useMemo(() => {
    if (filter === 'all') return classrooms
    return classrooms.filter((item) => item.is_active === (filter === 'active'))
  }, [classrooms, filter])

  function subjectName(subjectId?: string | null) {
    return subjects.find((subject) => subject.id === subjectId)?.name ?? 'Sem disciplina'
  }

  function edit(classroom: Classroom) {
    setEditingId(classroom.id)
    setForm({
      name: classroom.name,
      grade: classroom.grade ?? '',
      school_year: classroom.school_year ?? new Date().getFullYear(),
      subject_id: classroom.subject_id ?? '',
      description: classroom.description ?? '',
    })
  }

  function cancelEdit() {
    setEditingId(null)
    setForm(emptyForm)
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSuccess('')
    const payload = {
      name: form.name,
      grade: form.grade || null,
      school_year: form.school_year || null,
      subject_id: form.subject_id || null,
      description: form.description || null,
    }
    try {
      if (editingId) {
        await api<Classroom>(`/classrooms/${editingId}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
        setSuccess('Turma atualizada com sucesso.')
      } else {
        await api<Classroom>('/classrooms', {
          method: 'POST',
          body: JSON.stringify(payload),
        })
        setSuccess('Turma criada com sucesso.')
      }
      cancelEdit()
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao salvar turma.')
    }
  }

  async function toggleActive(classroom: Classroom) {
    try {
      if (classroom.is_active) {
        await api<void>(`/classrooms/${classroom.id}`, { method: 'DELETE' })
        setSuccess('Turma desativada.')
      } else {
        await api<Classroom>(`/classrooms/${classroom.id}`, {
          method: 'PATCH',
          body: JSON.stringify({ is_active: true }),
        })
        setSuccess('Turma reativada.')
      }
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao alterar turma.')
    }
  }

  async function openParticipants(classroom: Classroom) {
    setSelectedClassroom(classroom)
    setParticipantForm({ user_id: '', role: 'student' })
    try {
      setParticipants(await api<Enrollment[]>(`/classrooms/${classroom.id}/participants`))
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao carregar participantes.')
    }
  }

  async function addParticipant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedClassroom) return
    try {
      await api<Enrollment>(`/classrooms/${selectedClassroom.id}/participants`, {
        method: 'POST',
        body: JSON.stringify(participantForm),
      })
      setParticipantForm({ user_id: '', role: 'student' })
      setSuccess('Participante adicionado à turma.')
      await openParticipants(selectedClassroom)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao adicionar participante.')
    }
  }

  async function removeParticipant(enrollment: Enrollment) {
    if (!selectedClassroom) return
    const confirmed = window.confirm(`Remover ${enrollment.full_name} da turma?`)
    if (!confirmed) return
    try {
      await api<void>(
        `/classrooms/${selectedClassroom.id}/participants/${enrollment.id}`,
        { method: 'DELETE' },
      )
      setSuccess('Participante removido.')
      await openParticipants(selectedClassroom)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao remover participante.')
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <span className="eyebrow">GESTÃO ACADÊMICA</span>
          <h1>Turmas</h1>
          <p>Cadastre turmas, vincule disciplinas e gerencie participantes.</p>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}

      <div className="filter-bar">
        {(['all', 'active', 'inactive'] as const).map((item) => (
          <button key={item} type="button" className={filter === item ? 'filter active' : 'filter'} onClick={() => setFilter(item)}>
            {item === 'all' ? 'Todas' : item === 'active' ? 'Ativas' : 'Inativas'}
          </button>
        ))}
      </div>

      <div className="dashboard-grid">
        {canWrite ? (
          <form className="panel form-grid" onSubmit={submit}>
            <div className="panel-title-row">
              <h2>{editingId ? 'Editar turma' : 'Nova turma'}</h2>
              {editingId ? <button type="button" className="text-button" onClick={cancelEdit}>Cancelar</button> : null}
            </div>
            <label>Nome<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required /></label>
            <label>Ano/Série<input value={form.grade} onChange={(event) => setForm({ ...form, grade: event.target.value })} placeholder="Ex.: 6º ano" /></label>
            <label>Ano letivo<input type="number" min="2020" max="2100" value={form.school_year} onChange={(event) => setForm({ ...form, school_year: Number(event.target.value) })} /></label>
            <label>
              Disciplina
              <select value={form.subject_id} onChange={(event) => setForm({ ...form, subject_id: event.target.value })}>
                <option value="">Sem disciplina</option>
                {subjects.filter((item) => item.is_active).map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}
              </select>
            </label>
            <label>Descrição<textarea rows={4} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
            <button className="primary">{editingId ? 'Salvar turma' : 'Criar turma'}</button>
          </form>
        ) : (
          <aside className="panel permission-panel"><h2>Somente leitura</h2><p>Seu papel permite visualizar turmas e participantes.</p></aside>
        )}

        <div className="panel">
          <div className="panel-title-row"><h2>Turmas cadastradas</h2><span>{visibleClassrooms.length} turma(s)</span></div>
          <div className="classroom-list">
            {visibleClassrooms.map((classroom) => (
              <article className={`classroom-card ${!classroom.is_active ? 'inactive-card' : ''}`} key={classroom.id}>
                <div className="title-with-status"><strong>{classroom.name}</strong><small>{classroom.is_active ? 'Ativa' : 'Inativa'}</small></div>
                <span>{classroom.grade || 'Sem série definida'}</span>
                <span>{classroom.school_year || 'Ano não definido'} · {subjectName(classroom.subject_id)}</span>
                <p>{classroom.description || 'Sem descrição.'}</p>
                <div className="card-actions">
                  <button type="button" onClick={() => void openParticipants(classroom)}>Participantes</button>
                  {canWrite ? <button type="button" onClick={() => edit(classroom)}>Editar</button> : null}
                  {canWrite ? <button type="button" onClick={() => void toggleActive(classroom)}>{classroom.is_active ? 'Desativar' : 'Reativar'}</button> : null}
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>

      {selectedClassroom ? (
        <section className="panel participants-panel">
          <div className="panel-title-row">
            <div><h2>Participantes — {selectedClassroom.name}</h2><p className="muted">{participants.length} participante(s)</p></div>
            <button type="button" className="text-button" onClick={() => setSelectedClassroom(null)}>Fechar</button>
          </div>

          {canWrite ? (
            <form className="inline-form" onSubmit={addParticipant}>
              <select value={participantForm.user_id} onChange={(event) => setParticipantForm({ ...participantForm, user_id: event.target.value })} required>
                <option value="">Selecione um usuário</option>
                {directory.filter((person) => !participants.some((item) => item.user_id === person.id)).map((person) => <option key={person.id} value={person.id}>{person.full_name} — {person.email}</option>)}
              </select>
              <select value={participantForm.role} onChange={(event) => setParticipantForm({ ...participantForm, role: event.target.value as EnrollmentRole })}>
                <option value="student">Estudante</option>
                <option value="teacher">Professor</option>
                <option value="assistant">Assistente</option>
              </select>
              <button className="primary">Adicionar participante</button>
            </form>
          ) : null}

          <div className="participant-list">
            {participants.length === 0 ? <p>Nenhum participante cadastrado.</p> : participants.map((participant) => (
              <article key={participant.id}>
                <div className="avatar">{participant.full_name.slice(0, 2).toUpperCase()}</div>
                <div><strong>{participant.full_name}</strong><span>{participant.email}</span></div>
                <span className="role-chip">{enrollmentLabels[participant.role]}</span>
                {canWrite ? <button className="danger-button" type="button" onClick={() => void removeParticipant(participant)}>Remover</button> : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </section>
  )
}
