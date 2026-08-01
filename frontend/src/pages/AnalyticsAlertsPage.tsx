import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { EmptyState } from '../components/EmptyState'
import { LoadingState } from '../components/LoadingState'
import { api } from '../lib/api'
import type { LearningAlert } from '../types/analytics'

export function AnalyticsAlertsPage() {
  const [alerts, setAlerts] = useState<LearningAlert[]>([])
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    try {
      setAlerts(await api<LearningAlert[]>('/analytics/alerts'))
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Falha ao carregar alertas.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  async function changeStatus(id: string, status: LearningAlert['status']) {
    try {
      await api(`/analytics/alerts/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      })
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Falha ao atualizar alerta.')
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <span className="eyebrow">ALERTAS EXPLICÁVEIS</span>
          <h1>Alertas pedagógicos</h1>
          <p>Cada alerta informa a regra aplicada e as evidências consideradas.</p>
        </div>
        <Link className="secondary-button" to="/teacher/interventions">Orquestrar intervenções</Link>
      </header>

      {message ? <div className="inline-message" role="alert">{message}</div> : null}

      {loading ? <LoadingState label="Carregando alertas pedagógicos" rows={4} /> : alerts.length ? (
        <div className="alert-stack large">
          {alerts.map((alert) => (
            <article className={`learning-alert severity-${alert.severity}`} key={alert.id}>
              <div>
                <span>{alert.severity} · {alert.status}</span>
                <h2>{alert.title}</h2>
                <p>{alert.description}</p>
                <small>{alert.explanation}</small>
                <code>{alert.rule_code}</code>
              </div>
              <div className="alert-actions">
                <button onClick={() => void changeStatus(alert.id, 'acknowledged')}>Reconhecer</button>
                <button onClick={() => void changeStatus(alert.id, 'resolved')}>Resolver</button>
                <button onClick={() => void changeStatus(alert.id, 'dismissed')}>Descartar</button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState icon="alert" title="Nenhum alerta pedagógico" description="Quando uma regra identificar dificuldade, baixa conclusão ou abandono, o alerta aparecerá aqui com suas evidências." />
      )}
    </section>
  )
}
