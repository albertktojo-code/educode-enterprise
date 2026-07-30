import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'
import type { LearningAlert } from '../types/analytics'

export function AnalyticsAlertsPage() {
  const [alerts, setAlerts] = useState<LearningAlert[]>([])
  const [message, setMessage] = useState('')
  async function load() { setAlerts(await api<LearningAlert[]>('/analytics/alerts')) }
  useEffect(() => { void load().catch((error: Error) => setMessage(error.message)) }, [])
  async function changeStatus(id: string, status: LearningAlert['status']) {
    await api(`/analytics/alerts/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }); await load()
  }
  return <section><header className="page-header"><div><span className="eyebrow">ALERTAS EXPLICÁVEIS</span><h1>Alertas pedagógicos</h1><p>Cada alerta informa a regra aplicada e as evidências consideradas.</p></div><Link to="/teacher/interventions">Orquestrar intervenções</Link></header>{message ? <div className="inline-message">{message}</div> : null}<div className="alert-stack large">{alerts.map((alert) => <article className={`learning-alert severity-${alert.severity}`} key={alert.id}><div><span>{alert.severity} · {alert.status}</span><h2>{alert.title}</h2><p>{alert.description}</p><small>{alert.explanation}</small><code>{alert.rule_code}</code></div><div className="alert-actions"><button onClick={() => void changeStatus(alert.id, 'acknowledged')}>Reconhecer</button><button onClick={() => void changeStatus(alert.id, 'resolved')}>Resolver</button><button onClick={() => void changeStatus(alert.id, 'dismissed')}>Descartar</button></div></article>)}</div></section>
}
