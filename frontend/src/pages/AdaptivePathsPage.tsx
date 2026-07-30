import { useEffect, useState } from 'react'

import { api } from '../lib/api'
import type { LearningPath } from '../types/adaptive'

export function AdaptivePathsPage() {
  const [paths, setPaths] = useState<LearningPath[]>([])
  const [message, setMessage] = useState('')

  async function load() { setPaths(await api<LearningPath[]>('/adaptive/paths')) }
  useEffect(() => { void load().catch((error: Error) => setMessage(error.message)) }, [])

  async function changeStatus(path: LearningPath, status: 'active' | 'paused' | 'completed' | 'cancelled') {
    try {
      await api(`/adaptive/paths/${path.id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) })
      setMessage(`Trilha atualizada para ${status}.`)
      await load()
    } catch (error) { setMessage((error as Error).message) }
  }

  return (
    <section>
      <header className="page-header"><div><span className="eyebrow">TRILHAS PERSONALIZADAS</span><h1>Acompanhamento das trilhas</h1><p>Controle etapas, metas de domínio, revisões e resultados sem criar rótulos permanentes.</p></div></header>
      {message ? <div className="inline-message">{message}</div> : null}
      <div className="path-grid">
        {paths.map((path) => {
          const completed = path.steps.filter((step) => step.status === 'completed').length
          const progress = path.steps.length ? completed / path.steps.length * 100 : 0
          return <article className="path-card" key={path.id}>
            <div className="path-card-head"><span className={`status-pill status-${path.status}`}>{path.status}</span><small>{path.path_type.replaceAll('_', ' ')}</small></div>
            <h2>{path.title}</h2><p>{path.goal}</p>
            <div className="progress-track"><span style={{ width: `${progress}%` }} /></div><small>{completed} de {path.steps.length} etapas concluídas · meta {(path.target_mastery * 100).toFixed(0)}%</small>
            <ol className="path-steps">{path.steps.map((step) => <li className={`step-${step.status}`} key={step.id}><span>{step.position}</span><div><strong>{step.title}</strong><small>{step.status}</small></div></li>)}</ol>
            <div className="button-row"><button onClick={() => void changeStatus(path, 'active')} type="button">Ativar</button><button className="secondary-button" onClick={() => void changeStatus(path, 'paused')} type="button">Pausar</button><button className="secondary-button" onClick={() => void changeStatus(path, 'completed')} type="button">Concluir</button></div>
          </article>
        })}
        {!paths.length ? <article className="panel"><p className="muted">Nenhuma trilha criada. Aprove uma recomendação para iniciar.</p></article> : null}
      </div>
    </section>
  )
}
