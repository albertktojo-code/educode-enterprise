import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { EmptyState } from '../components/EmptyState'
import { LoadingState } from '../components/LoadingState'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import type {
  Classroom,
  Project,
  ProjectStatus,
  Subject,
} from '../types/education'

const statusLabels: Record<ProjectStatus, string> = {
  draft: 'Rascunho',
  active: 'Ativo',
  archived: 'Arquivado',
}

const emptyForm = {
  title: '',
  description: '',
  status: 'draft' as ProjectStatus,
  subject_id: '',
  classroom_id: '',
}

export function ProjectsPage() {
  const { user } = useAuth()
  const role = user?.memberships[0]?.role
  const canWrite = ['owner', 'admin', 'teacher'].includes(role ?? '')
  const canDelete = ['owner', 'admin'].includes(role ?? '')
  const [projects, setProjects] = useState<Project[]>([])
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [classrooms, setClassrooms] = useState<Classroom[]>([])
  const [editingId, setEditingId] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | ProjectStatus>('all')
  const [search, setSearch] = useState('')
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    try {
      const [projectData, subjectData, classroomData] = await Promise.all([
        api<Project[]>('/projects'),
        api<Subject[]>('/subjects'),
        api<Classroom[]>('/classrooms'),
      ])
      setProjects(projectData)
      setSubjects(subjectData)
      setClassrooms(classroomData)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao carregar projetos.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const visibleProjects = useMemo(() => {
    return projects.filter((project) => {
      const matchesStatus = filter === 'all' || project.status === filter
      const query = search.trim().toLowerCase()
      const matchesSearch =
        !query ||
        project.title.toLowerCase().includes(query) ||
        (project.description ?? '').toLowerCase().includes(query)
      return matchesStatus && matchesSearch
    })
  }, [filter, projects, search])

  function subjectName(id?: string | null) {
    return subjects.find((item) => item.id === id)?.name ?? 'Sem disciplina'
  }

  function classroomName(id?: string | null) {
    return classrooms.find((item) => item.id === id)?.name ?? 'Sem turma'
  }

  function edit(project: Project) {
    setEditingId(project.id)
    setForm({
      title: project.title,
      description: project.description ?? '',
      status: project.status,
      subject_id: project.subject_id ?? '',
      classroom_id: project.classroom_id ?? '',
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
      title: form.title,
      description: form.description || null,
      status: form.status,
      subject_id: form.subject_id || null,
      classroom_id: form.classroom_id || null,
    }
    try {
      if (editingId) {
        await api<Project>(`/projects/${editingId}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
        setSuccess('Projeto atualizado com sucesso.')
      } else {
        await api<Project>('/projects', {
          method: 'POST',
          body: JSON.stringify(payload),
        })
        setSuccess('Projeto criado com sucesso.')
      }
      cancelEdit()
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao salvar projeto.')
    }
  }

  async function changeStatus(project: Project, status: ProjectStatus) {
    setError('')
    try {
      await api<Project>(`/projects/${project.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      })
      setSuccess(`Projeto alterado para ${statusLabels[status]}.`)
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao alterar status.')
    }
  }

  async function deleteProject(project: Project) {
    const confirmed = window.confirm(
      `Excluir definitivamente o projeto "${project.title}" e todos os conteúdos?`,
    )
    if (!confirmed) return
    try {
      await api<void>(`/projects/${project.id}`, { method: 'DELETE' })
      setSuccess('Projeto excluído com sucesso.')
      if (editingId === project.id) cancelEdit()
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao excluir projeto.')
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <span className="eyebrow">PROJETOS EDUCACIONAIS</span>
          <h1>Projetos</h1>
          <p>Organize aulas, HQs, quizzes, atividades e referências.</p>
        </div>
      </header>

      {error ? <div className="alert error" role="alert">{error}</div> : null}
      {success ? <div className="alert success" role="status">{success}</div> : null}

      <div className="toolbar data-toolbar" aria-label="Filtros de projetos">
        <div className="filter-bar">
          {(['all', 'draft', 'active', 'archived'] as const).map((item) => (
            <button
              className={filter === item ? 'filter active' : 'filter'}
              key={item}
              onClick={() => setFilter(item)}
              type="button"
              aria-pressed={filter === item}
            >
              {item === 'all' ? 'Todos' : statusLabels[item]}
            </button>
          ))}
        </div>
        <label className="search-field">
          <span className="sr-only">Buscar projetos</span>
          <input
            className="search-input"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar projeto..."
          />
        </label>
      </div>

      <div className="dashboard-grid">
        {canWrite ? (
          <form className="panel form-grid" onSubmit={submit}>
            <div className="panel-title-row">
              <h2>{editingId ? 'Editar projeto' : 'Novo projeto'}</h2>
              {editingId ? <button className="text-button" type="button" onClick={cancelEdit}>Cancelar</button> : null}
            </div>
            <label>Título<input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required /></label>
            <label>Descrição<textarea rows={4} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
            <label>
              Status
              <select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value as ProjectStatus })}>
                <option value="draft">Rascunho</option>
                <option value="active">Ativo</option>
                <option value="archived">Arquivado</option>
              </select>
            </label>
            <label>
              Disciplina
              <select value={form.subject_id} onChange={(event) => setForm({ ...form, subject_id: event.target.value })}>
                <option value="">Sem disciplina</option>
                {subjects.filter((item) => item.is_active).map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}
              </select>
            </label>
            <label>
              Turma
              <select value={form.classroom_id} onChange={(event) => setForm({ ...form, classroom_id: event.target.value })}>
                <option value="">Sem turma</option>
                {classrooms.filter((item) => item.is_active).map((classroom) => <option key={classroom.id} value={classroom.id}>{classroom.name}</option>)}
              </select>
            </label>
            <button className="primary">{editingId ? 'Salvar projeto' : 'Criar projeto'}</button>
          </form>
        ) : (
          <aside className="panel permission-panel"><h2>Acesso de consulta</h2><p>Seu papel permite visualizar projetos e conteúdos.</p></aside>
        )}

        <div className="panel">
          <div className="panel-title-row"><h2>Projetos cadastrados</h2><span aria-live="polite">{visibleProjects.length} projeto(s)</span></div>
          {loading ? <LoadingState label="Carregando projetos" /> : visibleProjects.length === 0 ? (
            <EmptyState
              icon={projects.length ? 'search' : 'folder'}
              title={projects.length ? 'Nenhum resultado encontrado' : 'Seu primeiro projeto começa aqui'}
              description={projects.length ? 'Ajuste a busca ou os filtros para encontrar outro projeto.' : 'Crie um projeto para reunir conteúdos, HQs, avaliações e referências.'}
              action={projects.length ? <button type="button" className="text-button" onClick={() => { setFilter('all'); setSearch('') }}>Limpar filtros</button> : null}
            />
          ) : (
            <div className="project-list">
              {visibleProjects.map((project) => (
                <article className="project-card" key={project.id}>
                  <div className="project-card-heading">
                    <div>
                      <strong>{project.title}</strong>
                      <p>{project.description || 'Sem descrição.'}</p>
                      <small>{subjectName(project.subject_id)} · {classroomName(project.classroom_id)}</small>
                    </div>
                    <span className={`status-chip ${project.status}`}>{statusLabels[project.status]}</span>
                  </div>
                  <div className="card-actions">
                    <Link className="secondary-button" to={`/projetos/${project.id}`}>Abrir conteúdos</Link>
                    {canWrite ? <button type="button" onClick={() => edit(project)}>Editar</button> : null}
                    {canWrite && project.status !== 'active' ? <button type="button" onClick={() => void changeStatus(project, 'active')}>Ativar</button> : null}
                    {canWrite && project.status !== 'archived' ? <button type="button" onClick={() => void changeStatus(project, 'archived')}>Arquivar</button> : null}
                    {canWrite && project.status !== 'draft' ? <button type="button" onClick={() => void changeStatus(project, 'draft')}>Rascunho</button> : null}
                    {canDelete ? <button type="button" className="danger-button" onClick={() => void deleteProject(project)}>Excluir</button> : null}
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
