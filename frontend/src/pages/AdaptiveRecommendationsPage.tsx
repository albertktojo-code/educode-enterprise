import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'
import type { Recommendation } from '../types/adaptive'

export function AdaptiveRecommendationsPage() {
  const [items, setItems] = useState<Recommendation[]>([])
  const [statusFilter, setStatusFilter] = useState('pending_review')
  const [message, setMessage] = useState('')
  const [busyId, setBusyId] = useState('')

  async function load(filter = statusFilter) {
    const query = filter ? `?status=${filter}` : ''
    setItems(await api<Recommendation[]>(`/adaptive/recommendations${query}`))
  }

  useEffect(() => { void load().catch((error: Error) => setMessage(error.message)) }, [])

  async function decide(item: Recommendation, decision: 'approved' | 'rejected' | 'changes_requested') {
    setBusyId(item.id); setMessage('')
    try {
      await api(`/adaptive/recommendations/${item.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ decision, review_notes: decision === 'approved' ? 'Recomendação revisada e aprovada pelo professor.' : '' }),
      })
      if (decision === 'approved') {
        await api(`/adaptive/recommendations/${item.id}/create-path`, { method: 'POST' })
        setMessage('Recomendação aprovada e convertida em trilha ativa.')
      } else setMessage('Decisão registrada com rastreabilidade.')
      await load(statusFilter)
    } catch (error) { setMessage((error as Error).message) } finally { setBusyId('') }
  }

  return (
    <section>
      <header className="page-header"><div><span className="eyebrow">REVISÃO HUMANA</span><h1>Recomendações adaptativas</h1><p>Analise as evidências, edite os materiais propostos e decida o que será enviado ao estudante.</p></div><Link className="secondary-button" to="/adaptativo">Voltar ao painel</Link></header>
      {message ? <div className="inline-message">{message}</div> : null}
      <div className="filter-bar">
        {['pending_review', 'approved', 'rejected', 'changes_requested', ''].map((filter) => <button className={statusFilter === filter ? 'filter active' : 'filter'} key={filter || 'all'} onClick={() => { setStatusFilter(filter); void load(filter) }} type="button">{filter ? filter.replaceAll('_', ' ') : 'Todas'}</button>)}
      </div>
      <div className="recommendation-grid">
        {items.map((item) => (
          <article className={`recommendation-card priority-${item.priority}`} key={item.id}>
            <div className="recommendation-head"><span className="status-pill">{item.recommendation_type.replaceAll('_', ' ')}</span><small>confiança {(item.confidence_score * 100).toFixed(0)}%</small></div>
            <h2>{item.title}</h2><p>{item.rationale}</p>
            <div className="evidence-box"><strong>Evidências utilizadas</strong><pre>{JSON.stringify(item.evidence_summary, null, 2)}</pre></div>
            <div><strong>Materiais propostos</strong><ul>{item.proposed_materials.map((material, index) => <li key={`${item.id}-${index}`}>{String(material.title ?? material.type ?? 'Material')}</li>)}</ul></div>
            <div className="button-row">
              {item.student_id ? <Link className="text-button" to={`/adaptativo/estudantes/${item.student_id}`}>Ver perfil</Link> : null}
              {item.status === 'pending_review' ? <><button disabled={busyId === item.id} onClick={() => void decide(item, 'approved')} type="button">Aprovar e criar trilha</button><button className="secondary-button" disabled={busyId === item.id} onClick={() => void decide(item, 'changes_requested')} type="button">Solicitar ajustes</button><button className="danger-button" disabled={busyId === item.id} onClick={() => void decide(item, 'rejected')} type="button">Rejeitar</button></> : null}
            </div>
          </article>
        ))}
        {!items.length ? <article className="panel"><p className="muted">Nenhuma recomendação encontrada para o filtro atual.</p></article> : null}
      </div>
    </section>
  )
}
