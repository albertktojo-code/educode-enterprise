import { useEffect, useState } from 'react'

import { api } from '../lib/api'

type AuditEvent = {
  id: string
  module_name: string
  action: string
  entity_type: string
  entity_id: string | null
  request_id: string
  details: Record<string, unknown>
  event_hash: string
  created_at: string
}

type ChainStatus = { valid: boolean; events: number; broken_event_ids: string[] }

type Integrity = { status: string; checked_at: string; findings: Array<{ code: string; severity: string; count: number; description: string }> }

export function AdminAuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [chain, setChain] = useState<ChainStatus | null>(null)
  const [integrity, setIntegrity] = useState<Integrity | null>(null)

  async function load() {
    const [eventData, chainData, integrityData] = await Promise.all([
      api.get<AuditEvent[]>('/platform/audit-events?limit=300'),
      api.get<ChainStatus>('/platform/audit-events/verify'),
      api.get<Integrity>('/platform/integrity'),
    ])
    setEvents(eventData)
    setChain(chainData)
    setIntegrity(integrityData)
  }

  useEffect(() => { void load() }, [])

  return <div className="page-stack">
    <header className="page-header"><div><span className="eyebrow">Governança</span><h1>Auditoria e integridade</h1><p>Eventos críticos encadeados por hash e verificações de consistência dos dados educacionais.</p></div><button type="button" onClick={() => void load()}>Verificar novamente</button></header>
    <section className="stats stats-four">
      <article><strong>{chain?.valid ? 'Íntegra' : 'Atenção'}</strong><span>Cadeia de auditoria</span></article>
      <article><strong>{chain?.events ?? 0}</strong><span>Eventos verificados</span></article>
      <article><strong>{integrity?.status ?? '...'}</strong><span>Integridade de dados</span></article>
      <article><strong>{integrity?.findings.reduce((sum, finding) => sum + finding.count, 0) ?? 0}</strong><span>Ocorrências</span></article>
    </section>
    <section className="panel"><h2>Verificações de integridade</h2><div className="card-list">{integrity?.findings.map((finding) => <article className="compact-card" key={finding.code}><strong>{finding.code}</strong><span>{finding.severity} · {finding.count} ocorrência(s)</span><small>{finding.description}</small></article>)}</div></section>
    <section className="panel"><h2>Linha do tempo imutável</h2><div className="card-list">{events.length ? events.map((event) => <article className="compact-card" key={event.id}><strong>{event.module_name} · {event.action}</strong><span>{event.entity_type} {event.entity_id ?? ''}</span><small>{new Date(event.created_at).toLocaleString('pt-BR')} · request {event.request_id || 'não informado'} · hash {event.event_hash.slice(0, 16)}…</small></article>) : <p>Nenhum evento crítico registrado.</p>}</div></section>
  </div>
}
