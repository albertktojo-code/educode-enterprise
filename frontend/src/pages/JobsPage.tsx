import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'

type Job = {
  id: string
  job_type: string
  queue_name: string
  module_name: string
  status: string
  priority: number
  progress_percent: number
  current_step: string
  retry_count: number
  max_retries: number
  error_message: string
  created_at: string
  updated_at: string
}

const statusLabels: Record<string, string> = {
  pending: 'Pendente',
  queued: 'Na fila',
  processing: 'Processando',
  waiting_provider: 'Aguardando provedor',
  validating: 'Validando',
  retrying: 'Tentando novamente',
  completed: 'Concluída',
  failed: 'Falhou',
  cancelled: 'Cancelada',
  expired: 'Expirada',
}

export function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')

  async function load() {
    try {
      const suffix = status ? `?status=${encodeURIComponent(status)}` : ''
      setJobs(await api<Job[]>(`/jobs${suffix}`))
      setError('')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Não foi possível carregar as tarefas.')
    }
  }

  useEffect(() => {
    void load()
    const timer = window.setInterval(() => void load(), 3000)
    return () => window.clearInterval(timer)
  }, [status])

  const activeCount = useMemo(
    () => jobs.filter((job) => ['pending', 'queued', 'processing', 'retrying'].includes(job.status)).length,
    [jobs],
  )

  async function cancel(jobId: string) {
    await api(`/jobs/${jobId}/cancel`, { method: 'POST' })
    await load()
  }

  async function retry(jobId: string) {
    await api(`/jobs/${jobId}/retry`, { method: 'POST' })
    await load()
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="eyebrow">Sprint 12.2</span>
          <h1>Tarefas e processamentos</h1>
          <p>Acompanhe gerações de IA, documentos, relatórios, importações e recálculos sem bloquear o EduCode.</p>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}

      <section className="stats stats-four">
        <article><strong>{jobs.length}</strong><span>Tarefas exibidas</span></article>
        <article><strong>{activeCount}</strong><span>Em andamento</span></article>
        <article><strong>{jobs.filter((job) => job.status === 'completed').length}</strong><span>Concluídas</span></article>
        <article><strong>{jobs.filter((job) => job.status === 'failed').length}</strong><span>Falhas</span></article>
      </section>

      <section className="panel">
        <div className="panel-heading-row">
          <div>
            <h2>Fila da organização</h2>
            <p>Atualização automática a cada três segundos.</p>
          </div>
          <label>
            Status
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">Todos</option>
              {Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
        </div>
        <div className="card-list">
          {jobs.length ? jobs.map((job) => (
            <article className="compact-card" key={job.id}>
              <div className="job-card-header">
                <div>
                  <strong>{job.job_type}</strong>
                  <span>{job.module_name} · fila {job.queue_name} · prioridade {job.priority}</span>
                </div>
                <span className={`status-pill status-${job.status}`}>{statusLabels[job.status] ?? job.status}</span>
              </div>
              <div className="progress-track" aria-label={`Progresso ${job.progress_percent}%`}>
                <span style={{ width: `${job.progress_percent}%` }} />
              </div>
              <div className="job-meta-row">
                <span>{job.progress_percent}% · {job.current_step}</span>
                <span>Tentativas: {job.retry_count}/{job.max_retries}</span>
              </div>
              {job.error_message ? <small className="error-text">{job.error_message}</small> : null}
              <div className="button-row">
                <Link className="secondary-button" to={`/tarefas/${job.id}`}>Abrir detalhes</Link>
                {!['completed', 'failed', 'cancelled', 'expired'].includes(job.status) ? (
                  <button className="secondary" type="button" onClick={() => void cancel(job.id)}>Cancelar</button>
                ) : null}
                {['failed', 'cancelled'].includes(job.status) ? (
                  <button type="button" onClick={() => void retry(job.id)}>Tentar novamente</button>
                ) : null}
              </div>
            </article>
          )) : <p>Nenhuma tarefa encontrada.</p>}
        </div>
      </section>
    </div>
  )
}
