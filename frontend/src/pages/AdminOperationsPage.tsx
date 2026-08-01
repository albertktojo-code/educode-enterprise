import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'

type Overview = {
  redis_available: boolean
  worker_count: number
  active_workers: number
  queue_counts: Record<string, number>
  status_counts: Record<string, number>
  failed_last_24h: number
  average_completion_seconds: number
  circuit_open_count: number
}

type Worker = {
  id: string
  worker_name: string
  queue_name: string
  hostname: string
  process_id: number
  current_job_id: string | null
  status: string
  last_seen_at: string
}

type Failure = {
  id: string
  job_type: string
  module_name: string
  error_code: string
  error_message: string
  completed_at: string | null
}

export function AdminOperationsPage() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [workers, setWorkers] = useState<Worker[]>([])
  const [failures, setFailures] = useState<Failure[]>([])

  async function load() {
    const [overviewData, workerData, failureData] = await Promise.all([
      api<Overview>('/operations/overview'),
      api<Worker[]>('/operations/workers'),
      api<Failure[]>('/operations/failures'),
    ])
    setOverview(overviewData)
    setWorkers(workerData)
    setFailures(failureData)
  }

  useEffect(() => {
    void load()
    const timer = window.setInterval(() => void load(), 5000)
    return () => window.clearInterval(timer)
  }, [])

  return <div className="page-stack">
    <header className="page-header"><div><span className="eyebrow">Administração</span><h1>Operação e filas</h1><p>Saúde do Redis, workers, filas, falhas e circuitos dos provedores.</p></div></header>
    {overview ? <>
      <section className="stats stats-four">
        <article><strong>{overview.redis_available ? 'Online' : 'Indisponível'}</strong><span>Redis</span></article>
        <article><strong>{overview.active_workers}/{overview.worker_count}</strong><span>Workers ativos</span></article>
        <article><strong>{overview.failed_last_24h}</strong><span>Falhas em 24h</span></article>
        <article><strong>{overview.average_completion_seconds}s</strong><span>Tempo médio</span></article>
      </section>
      <section className="panel-grid two">
        <section className="panel"><h2>Filas pendentes</h2><div className="metric-grid">{Object.entries(overview.queue_counts).map(([name, count]) => <article key={name}><strong>{count}</strong><span>{name}</span></article>)}</div>{!Object.keys(overview.queue_counts).length ? <p>Nenhuma tarefa aguardando.</p> : null}</section>
        <section className="panel"><h2>Status das tarefas</h2><div className="metric-grid">{Object.entries(overview.status_counts).map(([name, count]) => <article key={name}><strong>{count}</strong><span>{name}</span></article>)}</div></section>
      </section>
    </> : <p>Carregando operação...</p>}
    <section className="panel"><h2>Workers</h2><div className="card-list">{workers.map((worker) => <article className="compact-card" key={worker.id}><strong>{worker.worker_name}</strong><span>Fila {worker.queue_name} · {worker.status} · PID {worker.process_id}</span><small>Último sinal: {new Date(worker.last_seen_at).toLocaleString('pt-BR')}</small>{worker.current_job_id ? <Link to={`/tarefas/${worker.current_job_id}`}>Abrir tarefa atual</Link> : null}</article>)}</div></section>
    <section className="panel"><h2>Fila de falhas</h2><div className="card-list">{failures.length ? failures.map((failure) => <article className="compact-card" key={failure.id}><strong>{failure.job_type} · {failure.module_name}</strong><span>{failure.error_code || 'ERRO'} — {failure.error_message}</span><Link className="secondary-button" to={`/tarefas/${failure.id}`}>Diagnosticar</Link></article>) : <p>Nenhuma falha registrada.</p>}</div></section>
  </div>
}
