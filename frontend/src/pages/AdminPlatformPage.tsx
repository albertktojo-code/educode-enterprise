import { useEffect, useState } from 'react'

import { api } from '../lib/api'

type Diagnostics = {
  overall_status: string
  version: {
    application: string
    version: string
    build_identifier: string
    commit_sha: string
    environment: string
    migration_revision: string
    maintenance_mode: boolean
  }
  dependencies: Array<{ name: string; status: string; latency_ms: number }>
  storage: Record<string, { writable?: boolean; free_bytes?: number; path?: string }>
  workers: { total: number; active: number; queues: string[]; stale_workers: string[] }
  warnings: string[]
}

type Backup = {
  id: string
  backup_type: string
  status: string
  size_bytes: number
  checksum_sha256: string
  created_at: string
  completed_at: string | null
  error_message: string
}

type Incident = {
  id: string
  title: string
  severity: string
  status: string
  affected_service: string
  impact: string
  started_at: string
}

type FeatureFlag = {
  id: string
  flag_key: string
  is_enabled: boolean
  scope_type: string
  description: string
}

function formatBytes(value: number) {
  if (!value) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1)
  return `${(value / 1024 ** index).toFixed(index ? 1 : 0)} ${units[index]}`
}

export function AdminPlatformPage() {
  const [diagnostics, setDiagnostics] = useState<Diagnostics | null>(null)
  const [backups, setBackups] = useState<Backup[]>([])
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [flags, setFlags] = useState<FeatureFlag[]>([])
  const [message, setMessage] = useState('')
  const [incidentTitle, setIncidentTitle] = useState('')

  async function load() {
    const [diagnosticData, backupData, incidentData, flagData] = await Promise.all([
      api.get<Diagnostics>('/platform/diagnostics'),
      api.get<Backup[]>('/platform/backups'),
      api.get<Incident[]>('/platform/incidents'),
      api.get<FeatureFlag[]>('/platform/feature-flags'),
    ])
    setDiagnostics(diagnosticData)
    setBackups(backupData)
    setIncidents(incidentData)
    setFlags(flagData)
  }

  useEffect(() => {
    void load()
  }, [])

  async function createBackup() {
    setMessage('Solicitando backup...')
    await api.post('/platform/backups', { backup_type: 'full', retention_days: 30 })
    setMessage('Backup enviado para a fila de tarefas.')
    await load()
  }

  async function verifyBackup(id: string) {
    setMessage('Enviando teste real de restauração para a fila...')
    await api.post(`/platform/backups/${id}/verify`)
    setMessage('Teste de restauração agendado. Acompanhe o resultado em Tarefas.')
  }

  async function createIncident() {
    if (!incidentTitle.trim()) return
    await api.post('/platform/incidents', {
      title: incidentTitle,
      severity: 'medium',
      affected_service: 'platform',
      impact: '',
    })
    setIncidentTitle('')
    await load()
  }

  async function toggleFlag(flag: FeatureFlag) {
    await api.put(`/platform/feature-flags/${flag.flag_key}`, {
      flag_key: flag.flag_key,
      is_enabled: !flag.is_enabled,
      scope_type: flag.scope_type,
      scope_id: null,
      configuration: {},
      description: flag.description,
    })
    await load()
  }

  return <div className="page-stack">
    <header className="page-header">
      <div><span className="eyebrow">Homologação</span><h1>Plataforma e recuperação</h1><p>Diagnóstico, versões, backups, incidentes e liberação gradual de recursos.</p></div>
      <button type="button" onClick={() => void load()}>Atualizar diagnóstico</button>
    </header>

    {message ? <div className="notice">{message}</div> : null}

    {diagnostics ? <>
      <section className="stats stats-four">
        <article><strong>{diagnostics.overall_status}</strong><span>Estado geral</span></article>
        <article><strong>{diagnostics.version.version}</strong><span>Versão</span></article>
        <article><strong>{diagnostics.version.migration_revision}</strong><span>Migration</span></article>
        <article><strong>{diagnostics.workers.active}/{diagnostics.workers.total}</strong><span>Workers ativos</span></article>
      </section>
      <section className="panel-grid two">
        <section className="panel"><h2>Dependências</h2><div className="card-list">{diagnostics.dependencies.map((item) => <article className="compact-card" key={item.name}><strong>{item.name}</strong><span>{item.status} · {item.latency_ms} ms</span></article>)}</div></section>
        <section className="panel"><h2>Armazenamento</h2><div className="card-list">{Object.entries(diagnostics.storage).map(([name, item]) => <article className="compact-card" key={name}><strong>{name}</strong><span>{item.writable ? 'Gravável' : 'Indisponível'} · livre {formatBytes(item.free_bytes ?? 0)}</span><small>{item.path}</small></article>)}</div></section>
      </section>
      {diagnostics.warnings.length ? <section className="panel"><h2>Avisos de homologação</h2>{diagnostics.warnings.map((warning) => <p key={warning}>{warning}</p>)}</section> : null}
    </> : <p>Carregando diagnóstico...</p>}

    <section className="panel">
      <div className="panel-heading"><div><h2>Backups auditáveis</h2><p>O PostgreSQL e os arquivos são empacotados com checksum.</p></div><button type="button" onClick={() => void createBackup()}>Criar backup completo</button></div>
      <div className="card-list">{backups.length ? backups.map((backup) => <article className="compact-card" key={backup.id}><strong>{backup.backup_type} · {backup.status}</strong><span>{new Date(backup.created_at).toLocaleString('pt-BR')} · {formatBytes(backup.size_bytes)}</span><small>{backup.checksum_sha256 || backup.error_message || 'Aguardando processamento'}</small>{backup.status === 'completed' ? <button className="secondary-button" type="button" onClick={() => void verifyBackup(backup.id)}>Testar restauração</button> : null}</article>) : <p>Nenhum backup registrado.</p>}</div>
    </section>

    <section className="panel-grid two">
      <section className="panel"><h2>Incidentes</h2><div className="inline-form"><input value={incidentTitle} onChange={(event) => setIncidentTitle(event.target.value)} placeholder="Descreva o incidente"/><button type="button" onClick={() => void createIncident()}>Registrar</button></div><div className="card-list">{incidents.map((incident) => <article className="compact-card" key={incident.id}><strong>{incident.title}</strong><span>{incident.severity} · {incident.status} · {incident.affected_service}</span><small>{new Date(incident.started_at).toLocaleString('pt-BR')}</small></article>)}</div></section>
      <section className="panel"><h2>Feature flags</h2><div className="card-list">{flags.length ? flags.map((flag) => <article className="compact-card" key={flag.id}><strong>{flag.flag_key}</strong><span>{flag.is_enabled ? 'Ativo' : 'Desativado'} · {flag.scope_type}</span><small>{flag.description}</small><button className="secondary-button" type="button" onClick={() => void toggleFlag(flag)}>{flag.is_enabled ? 'Desativar' : 'Ativar'}</button></article>) : <p>Cadastre flags pela API para liberar funcionalidades gradualmente.</p>}</div></section>
    </section>
  </div>
}
