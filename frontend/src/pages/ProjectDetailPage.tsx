import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import type { ContentItem, ContentType, Project } from '../types/education'

const contentLabels: Record<ContentType, string> = {
  lesson: 'Aula',
  comic: 'HQ',
  quiz: 'Quiz',
  activity: 'Atividade',
  reference: 'Referência',
}

const emptyForm = {
  title: '',
  content_type: 'lesson' as ContentType,
  body: '',
  is_published: false,
}

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { user } = useAuth()
  const role = user?.memberships[0]?.role
  const canWrite = ['owner', 'admin', 'teacher'].includes(role ?? '')
  const [project, setProject] = useState<Project | null>(null)
  const [contents, setContents] = useState<ContentItem[]>([])
  const [filter, setFilter] = useState<'all' | ContentType>('all')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function load() {
    if (!projectId) return
    try {
      const [projectData, contentData] = await Promise.all([
        api<Project>(`/projects/${projectId}`),
        api<ContentItem[]>(`/projects/${projectId}/contents`),
      ])
      setProject(projectData)
      setContents(contentData)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao carregar projeto.')
    }
  }

  useEffect(() => {
    void load()
  }, [projectId])

  const visibleContents = useMemo(
    () => filter === 'all' ? contents : contents.filter((item) => item.content_type === filter),
    [contents, filter],
  )

  function edit(content: ContentItem) {
    setEditingId(content.id)
    setForm({
      title: content.title,
      content_type: content.content_type,
      body: content.body ?? '',
      is_published: content.is_published,
    })
  }

  function cancelEdit() {
    setEditingId(null)
    setForm(emptyForm)
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!projectId) return
    setError('')
    setSuccess('')
    const payload = {
      title: form.title,
      content_type: form.content_type,
      body: form.body || null,
      is_published: form.is_published,
      ...(editingId ? {} : { position: contents.length }),
    }
    try {
      if (editingId) {
        await api<ContentItem>(`/projects/${projectId}/contents/${editingId}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
        setSuccess('Conteúdo atualizado com sucesso.')
      } else {
        await api<ContentItem>(`/projects/${projectId}/contents`, {
          method: 'POST',
          body: JSON.stringify(payload),
        })
        setSuccess('Conteúdo adicionado ao projeto.')
      }
      cancelEdit()
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao salvar conteúdo.')
    }
  }

  async function patchContent(contentId: string, payload: Record<string, unknown>) {
    if (!projectId) return
    await api<ContentItem>(`/projects/${projectId}/contents/${contentId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  }

  async function togglePublished(content: ContentItem) {
    try {
      await patchContent(content.id, { is_published: !content.is_published })
      setSuccess(content.is_published ? 'Conteúdo despublicado.' : 'Conteúdo publicado.')
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao alterar publicação.')
    }
  }

  async function move(content: ContentItem, direction: -1 | 1) {
    const currentIndex = contents.findIndex((item) => item.id === content.id)
    const target = contents[currentIndex + direction]
    if (!target) return
    try {
      await patchContent(content.id, { position: target.position })
      await patchContent(target.id, { position: content.position })
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao reordenar conteúdo.')
    }
  }

  async function deleteContent(content: ContentItem) {
    if (!projectId || !window.confirm(`Excluir o conteúdo "${content.title}"?`)) return
    try {
      await api<void>(`/projects/${projectId}/contents/${content.id}`, { method: 'DELETE' })
      setSuccess('Conteúdo excluído.')
      if (editingId === content.id) cancelEdit()
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao excluir conteúdo.')
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <Link className="back-link" to="/projetos">← Voltar para projetos</Link>
          <span className="eyebrow">CONTEÚDOS DO PROJETO</span>
          <h1>{project?.title ?? 'Carregando projeto...'}</h1>
          <p>{project?.description || 'Projeto sem descrição.'}</p>
        </div>
        {project ? (
          <div className="header-actions">
            <span className={`status-chip ${project.status}`}>{project.status}</span>
            <Link className="secondary-button" to={`/documentos?project=${project.id}`}>
              Documentos do projeto
            </Link>
          </div>
        ) : null}
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}

      <div className="filter-bar">
        {(['all', 'lesson', 'comic', 'quiz', 'activity', 'reference'] as const).map((item) => (
          <button type="button" key={item} className={filter === item ? 'filter active' : 'filter'} onClick={() => setFilter(item)}>
            {item === 'all' ? 'Todos' : contentLabels[item]}
          </button>
        ))}
      </div>

      <div className="dashboard-grid">
        {canWrite ? (
          <form className="panel form-grid" onSubmit={submit}>
            <div className="panel-title-row">
              <h2>{editingId ? 'Editar conteúdo' : 'Novo conteúdo'}</h2>
              {editingId ? <button className="text-button" type="button" onClick={cancelEdit}>Cancelar</button> : null}
            </div>
            <label>
              Tipo de conteúdo
              <select value={form.content_type} onChange={(event) => setForm({ ...form, content_type: event.target.value as ContentType })}>
                <option value="lesson">Aula</option>
                <option value="comic">HQ</option>
                <option value="quiz">Quiz</option>
                <option value="activity">Atividade</option>
                <option value="reference">Referência</option>
              </select>
            </label>
            <label>Título<input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required /></label>
            <label>Texto, roteiro ou instruções<textarea rows={10} value={form.body} onChange={(event) => setForm({ ...form, body: event.target.value })} /></label>
            <label className="checkbox-row"><input type="checkbox" checked={form.is_published} onChange={(event) => setForm({ ...form, is_published: event.target.checked })} />Publicar conteúdo</label>
            <button className="primary">{editingId ? 'Salvar conteúdo' : 'Adicionar conteúdo'}</button>
          </form>
        ) : (
          <aside className="panel permission-panel"><h2>Somente leitura</h2><p>Seu papel permite consultar os conteúdos.</p></aside>
        )}

        <div className="panel">
          <div className="panel-title-row"><h2>Conteúdos</h2><span>{visibleContents.length} item(ns)</span></div>
          {visibleContents.length === 0 ? <p>Nenhum conteúdo encontrado.</p> : (
            <div className="content-list">
              {visibleContents.map((content) => (
                <article className="content-card" key={content.id}>
                  <div>
                    <span className={`content-type ${content.content_type}`}>{contentLabels[content.content_type]}</span>
                    <strong>{content.title}</strong>
                    <p className="content-preview">{content.body || 'Sem texto inicial.'}</p>
                    <small>Posição {content.position + 1}</small>
                  </div>
                  <div className="vertical-actions">
                    <span className={content.is_published ? 'publication-chip published' : 'publication-chip'}>{content.is_published ? 'Publicado' : 'Não publicado'}</span>
                    {canWrite ? (
                      <div className="card-actions compact">
                        <button type="button" onClick={() => edit(content)}>Editar</button>
                        <button type="button" onClick={() => void togglePublished(content)}>{content.is_published ? 'Despublicar' : 'Publicar'}</button>
                        <button type="button" onClick={() => void move(content, -1)} disabled={contents[0]?.id === content.id}>↑</button>
                        <button type="button" onClick={() => void move(content, 1)} disabled={contents[contents.length - 1]?.id === content.id}>↓</button>
                        <button type="button" className="danger-button" onClick={() => void deleteContent(content)}>Excluir</button>
                      </div>
                    ) : null}
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
