import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { api } from '../lib/api'

type Job = {
  id: string
  job_type: string
  module_name: string
  queue_name: string
  status: string
  progress_percent: number
  current_step: string
  retry_count: number
  max_retries: number
  input_snapshot: Record<string, unknown>
  result_reference: Record<string, unknown>
  error_code: string
  error_message: string
  ai_flow_id: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

type JobEvent = {
  id: string
  event_type: string
  event_data: Record<string, unknown>
  created_at: string
}

export function JobDetailPage() {
  const { jobId = '' } = useParams()
  const navigate = useNavigate()
  const [job, setJob] = useState<Job | null>(null)
  const [events, setEvents] = useState<JobEvent[]>([])
  const [error, setError] = useState('')

  async function load() {
    try {
      const [jobData, eventData] = await Promise.all([
        api<Job>(`/jobs/${jobId}`),
        api<JobEvent[]>(`/jobs/${jobId}/events`),
      ])
      setJob(jobData)
      setEvents(eventData)
      setError('')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Não foi possível carregar a tarefa.')
    }
  }

  useEffect(() => {
    void load()
    const timer = window.setInterval(() => void load(), 2000)
    return () => window.clearInterval(timer)
  }, [jobId])

  async function cancel() {
    await api(`/jobs/${jobId}/cancel`, { method: 'POST' })
    await load()
  }

  async function retry() {
    await api(`/jobs/${jobId}/retry`, { method: 'POST' })
    await load()
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="eyebrow">Execução rastreável</span>
          <h1>{job?.job_type ?? 'Detalhes da tarefa'}</h1>
          <p>{job?.module_name} · {job?.queue_name} {job?.ai_flow_id ? `· ${job.ai_flow_id}` : ''}</p>
        </div>
        <button className="secondary" type="button" onClick={() => navigate('/tarefas')}>Voltar</button>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {job ? <>
        <section className="panel-grid two">
          <section className="panel">
            <h2>Progresso</h2>
            <div className="progress-track large"><span style={{ width: `${job.progress_percent}%` }} /></div>
            <strong>{job.progress_percent}%</strong>
            <p>{job.current_step}</p>
            <div className="button-row">
              {!['completed', 'failed', 'cancelled', 'expired'].includes(job.status) ? <button type="button" onClick={() => void cancel()}>Cancelar</button> : null}
              {['failed', 'cancelled'].includes(job.status) ? <button type="button" onClick={() => void retry()}>Tentar novamente</button> : null}
            </div>
          </section>
          <section className="panel">
            <h2>Execução</h2>
            <dl className="detail-list">
              <div><dt>Status</dt><dd>{job.status}</dd></div>
              <div><dt>Tentativas</dt><dd>{job.retry_count}/{job.max_retries}</dd></div>
              <div><dt>Início</dt><dd>{job.started_at ? new Date(job.started_at).toLocaleString('pt-BR') : 'Não iniciada'}</dd></div>
              <div><dt>Conclusão</dt><dd>{job.completed_at ? new Date(job.completed_at).toLocaleString('pt-BR') : '—'}</dd></div>
            </dl>
            {job.error_message ? <div className="alert error"><strong>{job.error_code}</strong><br />{job.error_message}</div> : null}
          </section>
        </section>

        <section className="panel">
          <h2>Linha do tempo</h2>
          <div className="timeline-list">
            {events.map((event) => (
              <article key={event.id}>
                <span>{new Date(event.created_at).toLocaleString('pt-BR')}</span>
                <strong>{event.event_type}</strong>
                <pre>{JSON.stringify(event.event_data, null, 2)}</pre>
              </article>
            ))}
          </div>
        </section>

        <section className="panel-grid two">
          <section className="panel"><h2>Entrada congelada</h2><pre className="json-box">{JSON.stringify(job.input_snapshot, null, 2)}</pre></section>
          <section className="panel"><h2>Resultado</h2><pre className="json-box">{JSON.stringify(job.result_reference, null, 2)}</pre></section>
        </section>
      </> : null}
    </div>
  )
}
