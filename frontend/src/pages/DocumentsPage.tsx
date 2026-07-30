import { FormEvent, useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { useAuth } from '../contexts/AuthContext'
import { api, apiBlob } from '../lib/api'
import type { DocumentDetail, DocumentItem, DocumentStatus } from '../types/document'
import type { Project } from '../types/education'

const statusLabels: Record<DocumentStatus, string> = {
  uploaded: 'Enviado',
  processing: 'Processando',
  ready: 'Pronto',
  failed: 'Falhou',
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function DocumentsPage() {
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const role = user?.memberships[0]?.role
  const canWrite = ['owner', 'admin', 'teacher'].includes(role ?? '')
  const canDelete = ['owner', 'admin'].includes(role ?? '')

  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [selected, setSelected] = useState<DocumentDetail | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [projectId, setProjectId] = useState(searchParams.get('project') ?? '')
  const [autoProcess, setAutoProcess] = useState(true)
  const [statusFilter, setStatusFilter] = useState<'all' | DocumentStatus>('all')
  const [search, setSearch] = useState('')
  const [uploading, setUploading] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [fileInputKey, setFileInputKey] = useState(0)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function load() {
    setError('')
    try {
      const [documentData, projectData] = await Promise.all([
        api<DocumentItem[]>('/documents'),
        api<Project[]>('/projects'),
      ])
      setDocuments(documentData)
      setProjects(projectData)
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível carregar os documentos.',
      )
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const visibleDocuments = useMemo(() => {
    const query = search.trim().toLowerCase()
    return documents.filter((document) => {
      const matchesStatus =
        statusFilter === 'all' || document.status === statusFilter
      const matchesSearch =
        !query ||
        document.original_filename.toLowerCase().includes(query) ||
        document.checksum_sha256.toLowerCase().includes(query)
      const requestedProject = searchParams.get('project')
      const matchesProject =
        !requestedProject || document.project_id === requestedProject
      return matchesStatus && matchesSearch && matchesProject
    })
  }, [documents, search, searchParams, statusFilter])

  function projectName(id?: string | null) {
    return projects.find((project) => project.id === id)?.title ?? 'Sem projeto'
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!file) {
      setError('Selecione um arquivo PDF.')
      return
    }

    setUploading(true)
    setError('')
    setSuccess('')

    const data = new FormData()
    data.append('file', file)
    if (projectId) data.append('project_id', projectId)
    data.append('auto_process', String(autoProcess))

    try {
      const created = await api<DocumentDetail>('/documents/upload', {
        method: 'POST',
        body: data,
      })
      setSuccess(
        created.status === 'ready'
          ? 'PDF enviado e texto extraído com sucesso.'
          : 'PDF enviado com sucesso.',
      )
      setFile(null)
      setFileInputKey((value) => value + 1)
      setSelected(created)
      await load()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Falha ao enviar o documento.',
      )
    } finally {
      setUploading(false)
    }
  }

  async function viewDocument(document: DocumentItem) {
    setBusyId(document.id)
    setError('')
    try {
      setSelected(await api<DocumentDetail>(`/documents/${document.id}`))
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Falha ao abrir o documento.',
      )
    } finally {
      setBusyId(null)
    }
  }

  async function processDocument(document: DocumentItem) {
    setBusyId(document.id)
    setError('')
    setSuccess('')
    try {
      const updated = await api<DocumentDetail>(
        `/documents/${document.id}/process`,
        { method: 'POST' },
      )
      setSelected(updated)
      setSuccess(
        updated.status === 'ready'
          ? 'Texto extraído com sucesso.'
          : 'O processamento terminou com falha. Consulte os detalhes.',
      )
      await load()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Falha ao processar o documento.',
      )
    } finally {
      setBusyId(null)
    }
  }

  async function updateProject(document: DocumentItem, value: string) {
    setBusyId(document.id)
    setError('')
    try {
      await api<DocumentItem>(`/documents/${document.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ project_id: value || null }),
      })
      setSuccess('Vínculo do documento atualizado.')
      await load()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Falha ao atualizar o vínculo.',
      )
    } finally {
      setBusyId(null)
    }
  }

  async function download(document: DocumentItem) {
    setBusyId(document.id)
    setError('')
    try {
      const blob = await apiBlob(`/documents/${document.id}/download`)
      const url = URL.createObjectURL(blob)
      const link = window.document.createElement('a')
      link.href = url
      link.download = document.original_filename
      link.click()
      URL.revokeObjectURL(url)
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Falha ao baixar o documento.',
      )
    } finally {
      setBusyId(null)
    }
  }

  async function remove(document: DocumentItem) {
    if (!window.confirm(`Excluir permanentemente "${document.original_filename}"?`)) {
      return
    }
    setBusyId(document.id)
    setError('')
    try {
      await api<void>(`/documents/${document.id}`, { method: 'DELETE' })
      if (selected?.id === document.id) setSelected(null)
      setSuccess('Documento excluído.')
      await load()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Falha ao excluir o documento.',
      )
    } finally {
      setBusyId(null)
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <span className="eyebrow">BASE DOCUMENTAL</span>
          <h1>Documentos e PDFs</h1>
          <p>
            Envie materiais, extraia páginas e revise capítulos antes de usar
            o conteúdo no pipeline RAG.
          </p>
        </div>
        <button className="secondary-button" onClick={() => void load()}>
          Atualizar documentos
        </button>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}

      <div className="dashboard-grid wide-left">
        {canWrite ? (
          <form className="panel form-grid" onSubmit={upload}>
            <h2>Enviar novo PDF</h2>
            <label>
              Arquivo PDF
              <input
                key={fileInputKey}
                type="file"
                accept="application/pdf,.pdf"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                required
              />
            </label>
            <label>
              Vincular a projeto
              <select
                value={projectId}
                onChange={(event) => setProjectId(event.target.value)}
              >
                <option value="">Sem projeto</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={autoProcess}
                onChange={(event) => setAutoProcess(event.target.checked)}
              />
              Extrair o texto imediatamente
            </label>
            <button className="primary" disabled={uploading}>
              {uploading ? 'Enviando e processando...' : 'Enviar PDF'}
            </button>
            <small className="muted">
              Limite padrão: 25 MB. Apenas arquivos PDF válidos são aceitos.
            </small>
          </form>
        ) : (
          <aside className="panel permission-panel">
            <h2>Somente leitura</h2>
            <p>Seu papel permite consultar e baixar documentos.</p>
          </aside>
        )}

        <div className="panel">
          <h2>Resumo da base</h2>
          <div className="detail-list">
            <div>
              <span>Total</span>
              <strong>{documents.length}</strong>
            </div>
            <div>
              <span>Prontos para RAG</span>
              <strong>
                {documents.filter((item) => item.status === 'ready').length}
              </strong>
            </div>
            <div>
              <span>Falhas</span>
              <strong>
                {documents.filter((item) => item.status === 'failed').length}
              </strong>
            </div>
          </div>
        </div>
      </div>

      <section className="panel document-list-panel">
        <div className="panel-title-row">
          <div>
            <h2>Arquivos armazenados</h2>
            <p>{visibleDocuments.length} documento(s) visível(is)</p>
          </div>
          <input
            className="search-input"
            placeholder="Buscar por nome ou checksum"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        <div className="filter-bar">
          {(['all', 'uploaded', 'processing', 'ready', 'failed'] as const).map(
            (status) => (
              <button
                type="button"
                key={status}
                className={statusFilter === status ? 'filter active' : 'filter'}
                onClick={() => setStatusFilter(status)}
              >
                {status === 'all' ? 'Todos' : statusLabels[status]}
              </button>
            ),
          )}
        </div>

        {visibleDocuments.length === 0 ? (
          <p>Nenhum documento encontrado.</p>
        ) : (
          <div className="document-list">
            {visibleDocuments.map((document) => (
              <article className="document-card" key={document.id}>
                <div className="document-icon">PDF</div>
                <div className="document-main">
                  <div className="title-with-status">
                    <strong>{document.original_filename}</strong>
                    <span className={`document-status ${document.status}`}>
                      {statusLabels[document.status]}
                    </span>
                  </div>
                  <p>
                    {formatBytes(document.size_bytes)} ·{' '}
                    {document.page_count ?? 0} página(s) ·{' '}
                    {projectName(document.project_id)}
                  </p>
                  <small className="mono">
                    SHA-256: {document.checksum_sha256}
                  </small>
                  {document.processed_at ? (
                    <small>
                      Processado em{' '}
                      {new Date(document.processed_at).toLocaleString('pt-BR')}
                    </small>
                  ) : null}
                </div>
                <div className="document-actions">
                  {canWrite ? (
                    <select
                      aria-label={`Projeto de ${document.original_filename}`}
                      value={document.project_id ?? ''}
                      disabled={busyId === document.id}
                      onChange={(event) =>
                        void updateProject(document, event.target.value)
                      }
                    >
                      <option value="">Sem projeto</option>
                      {projects.map((project) => (
                        <option key={project.id} value={project.id}>
                          {project.title}
                        </option>
                      ))}
                    </select>
                  ) : null}
                  <div className="card-actions compact">
                    <button
                      type="button"
                      disabled={busyId === document.id}
                      onClick={() => navigate(`/documentos/${document.id}`)}
                    >
                      Estruturar PDF
                    </button>
                    <button
                      type="button"
                      disabled={busyId === document.id}
                      onClick={() => void viewDocument(document)}
                    >
                      Texto completo
                    </button>
                    <button
                      type="button"
                      disabled={busyId === document.id}
                      onClick={() => void download(document)}
                    >
                      Baixar
                    </button>
                    {canWrite ? (
                      <button
                        type="button"
                        disabled={busyId === document.id}
                        onClick={() => void processDocument(document)}
                      >
                        {document.status === 'ready' ? 'Reprocessar' : 'Processar'}
                      </button>
                    ) : null}
                    {canDelete ? (
                      <button
                        type="button"
                        className="danger-button"
                        disabled={busyId === document.id}
                        onClick={() => void remove(document)}
                      >
                        Excluir
                      </button>
                    ) : null}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {selected ? (
        <section className="panel document-preview-panel">
          <div className="panel-title-row">
            <div>
              <h2>Texto extraído</h2>
              <p>{selected.original_filename}</p>
            </div>
            <button className="text-button" onClick={() => setSelected(null)}>
              Fechar
            </button>
          </div>
          {selected.extraction_error ? (
            <div className="alert error">{selected.extraction_error}</div>
          ) : null}
          {selected.extracted_text ? (
            <pre className="extracted-text">{selected.extracted_text}</pre>
          ) : (
            <p>
              Nenhum texto foi extraído. Use o botão{' '}
              <strong>Processar</strong> para executar a extração.
            </p>
          )}
        </section>
      ) : null}
    </section>
  )
}
