import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { StatusCard } from '../components/StatusCard'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import type { DashboardSummary } from '../types/education'

type Health = {
  status: string
  service: string
  environment: string
  database: string
  ai_provider: string
}

const emptySummary: DashboardSummary = {
  subjects: 0,
  classrooms: 0,
  active_classrooms: 0,
  users: 0,
  projects: 0,
  draft_projects: 0,
  active_projects: 0,
  archived_projects: 0,
  contents: 0,
  published_contents: 0,
  documents: 0,
  ready_documents: 0,
}

export function DashboardPage() {
  const { user } = useAuth()
  const membership = user?.memberships[0]
  const [summary, setSummary] = useState(emptySummary)
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    setError('')
    try {
      const [summaryData, healthData] = await Promise.all([
        api<DashboardSummary>('/dashboard/summary'),
        api<Health>('/health', { auth: false }),
      ])
      setSummary(summaryData)
      setHealth(healthData)
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível atualizar o painel.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  return (
    <section>
      <header className="page-header">
        <div>
          <span className="eyebrow">PAINEL OPERACIONAL</span>
          <h1>Olá, {user?.full_name.split(' ')[0]}</h1>
          <p>
            Acompanhe a organização, o núcleo educacional e a infraestrutura
            em uma visão consolidada.
          </p>
        </div>
        <button className="secondary-button" onClick={() => void load()}>
          {loading ? 'Atualizando...' : 'Atualizar painel'}
        </button>
      </header>

      {error ? <div className="alert error" role="alert">{error}</div> : null}

      <section className="data-metric-grid data-metric-grid--five" aria-label="Resumo da organização">
        <StatusCard title="Projetos" value={summary.projects} detail={`${summary.active_projects} ativos`} state="info" loading={loading} />
        <StatusCard title="Conteúdos" value={summary.contents} detail={`${summary.published_contents} publicados`} state="success" loading={loading} />
        <StatusCard title="Turmas" value={summary.classrooms} detail={`${summary.active_classrooms} ativas`} state="neutral" loading={loading} />
        <StatusCard title="Equipe" value={summary.users} detail={`${summary.subjects} disciplinas`} state="neutral" loading={loading} />
        <StatusCard title="Documentos" value={summary.documents} detail={`${summary.ready_documents} prontos para RAG`} state="warning" loading={loading} />
      </section>

      <section className="dashboard-sections">
        <div className="panel">
          <div className="panel-title-row">
            <h2>Status da plataforma</h2>
            <span className={health ? 'online-dot' : 'offline-dot'} />
          </div>
          <div className="detail-list">
            <div><span>API</span><strong>{health?.status ?? 'Indisponível'}</strong></div>
            <div><span>Banco</span><strong>{health?.database ?? 'Indisponível'}</strong></div>
            <div><span>IA</span><strong>{health?.ai_provider ?? 'mock'}</strong></div>
            <div><span>Ambiente</span><strong>{health?.environment ?? '-'}</strong></div>
          </div>
        </div>

        <div className="panel">
          <h2>Projetos por status</h2>
          <div className="status-overview">
            <div><span className="status-chip draft">Rascunho</span><strong>{summary.draft_projects}</strong></div>
            <div><span className="status-chip active">Ativo</span><strong>{summary.active_projects}</strong></div>
            <div><span className="status-chip archived">Arquivado</span><strong>{summary.archived_projects}</strong></div>
          </div>
        </div>
      </section>

      <section className="panel">
        <h2>Ações rápidas</h2>
        <div className="quick-actions">
          <Link to="/projetos">Criar ou editar projeto</Link>
          <Link to="/turmas">Gerenciar turmas</Link>
          <Link to="/disciplinas">Organizar disciplinas</Link>
          <Link to="/documentos">Enviar e processar PDFs</Link>
          <Link to="/unidades-pedagogicas">Estruturar unidades pedagógicas</Link>
          <Link to="/estudio-pedagogico">Planejar materiais com PC</Link>
          <Link to="/biblioteca-criativa">Cadastrar personagens, cenários e estilos</Link>
          <Link to="/sequencias-didaticas">Montar sequência didática</Link>
          <Link to="/ia-mock">Testar IA mock</Link>
        </div>
        <p className="muted">
          Organização atual: <strong>{membership?.organization.name}</strong> ·
          papel: <strong>{membership?.role}</strong>.
        </p>
      </section>
    </section>
  )
}
