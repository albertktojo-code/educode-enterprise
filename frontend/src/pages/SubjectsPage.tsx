import { FormEvent, useEffect, useMemo, useState } from 'react'

import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import type { Subject } from '../types/education'

const emptyForm = { name: '', code: '', description: '' }

export function SubjectsPage() {
  const { user } = useAuth()
  const role = user?.memberships[0]?.role
  const canWrite = ['owner', 'admin', 'teacher'].includes(role ?? '')
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [editingId, setEditingId] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'active' | 'inactive'>('all')
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function load() {
    try {
      setSubjects(await api<Subject[]>('/subjects'))
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao carregar disciplinas.')
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const visibleSubjects = useMemo(() => {
    if (filter === 'all') return subjects
    return subjects.filter((item) => item.is_active === (filter === 'active'))
  }, [filter, subjects])

  function edit(subject: Subject) {
    setEditingId(subject.id)
    setForm({
      name: subject.name,
      code: subject.code,
      description: subject.description ?? '',
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
    try {
      if (editingId) {
        await api<Subject>(`/subjects/${editingId}`, {
          method: 'PATCH',
          body: JSON.stringify({
            name: form.name,
            code: form.code,
            description: form.description || null,
          }),
        })
        setSuccess('Disciplina atualizada com sucesso.')
      } else {
        await api<Subject>('/subjects', {
          method: 'POST',
          body: JSON.stringify({
            name: form.name,
            code: form.code,
            description: form.description || null,
          }),
        })
        setSuccess('Disciplina criada com sucesso.')
      }
      cancelEdit()
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao salvar disciplina.')
    }
  }

  async function toggleActive(subject: Subject) {
    setError('')
    try {
      if (subject.is_active) {
        await api<void>(`/subjects/${subject.id}`, { method: 'DELETE' })
        setSuccess('Disciplina desativada.')
      } else {
        await api<Subject>(`/subjects/${subject.id}`, {
          method: 'PATCH',
          body: JSON.stringify({ is_active: true }),
        })
        setSuccess('Disciplina reativada.')
      }
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao alterar disciplina.')
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <span className="eyebrow">ORGANIZAÇÃO PEDAGÓGICA</span>
          <h1>Disciplinas</h1>
          <p>
            Pensamento Computacional é criado pelo seed. Cadastre e mantenha
            outras áreas do conhecimento.
          </p>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}

      <div className="filter-bar">
        {(['all', 'active', 'inactive'] as const).map((item) => (
          <button
            type="button"
            key={item}
            className={filter === item ? 'filter active' : 'filter'}
            onClick={() => setFilter(item)}
          >
            {item === 'all' ? 'Todas' : item === 'active' ? 'Ativas' : 'Inativas'}
          </button>
        ))}
      </div>

      <div className="dashboard-grid">
        {canWrite ? (
          <form className="panel form-grid" onSubmit={submit}>
            <div className="panel-title-row">
              <h2>{editingId ? 'Editar disciplina' : 'Nova disciplina'}</h2>
              {editingId ? (
                <button className="text-button" type="button" onClick={cancelEdit}>
                  Cancelar
                </button>
              ) : null}
            </div>
            <label>
              Nome
              <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
            </label>
            <label>
              Código
              <input value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value.toUpperCase() })} required />
            </label>
            <label>
              Descrição
              <textarea rows={5} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
            </label>
            <button className="primary">{editingId ? 'Salvar disciplina' : 'Criar disciplina'}</button>
          </form>
        ) : (
          <aside className="panel permission-panel">
            <h2>Somente leitura</h2>
            <p>Seu papel permite consultar as disciplinas da organização.</p>
          </aside>
        )}

        <div className="panel">
          <div className="panel-title-row">
            <h2>Disciplinas cadastradas</h2>
            <span>{visibleSubjects.length} disciplina(s)</span>
          </div>
          <div className="subject-list">
            {visibleSubjects.map((subject) => (
              <article className={`subject-card ${!subject.is_active ? 'inactive-card' : ''}`} key={subject.id}>
                <span className="subject-code">{subject.code}</span>
                <div>
                  <div className="title-with-status">
                    <strong>{subject.name}</strong>
                    <small>{subject.is_active ? 'Ativa' : 'Inativa'}</small>
                  </div>
                  <p>{subject.description || 'Sem descrição.'}</p>
                  {canWrite ? (
                    <div className="card-actions">
                      <button type="button" onClick={() => edit(subject)}>Editar</button>
                      <button type="button" onClick={() => void toggleActive(subject)}>
                        {subject.is_active ? 'Desativar' : 'Reativar'}
                      </button>
                    </div>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
