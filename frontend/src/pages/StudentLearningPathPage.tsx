import { useEffect, useState } from 'react'

import { api } from '../lib/api'
import type { PathStep, StudentOwnPath } from '../types/adaptive'

function pct(value: number) { return `${(value * 100).toFixed(0)}%` }

export function StudentLearningPathPage() {
  const [data, setData] = useState<StudentOwnPath | null>(null)
  const [message, setMessage] = useState('')
  const [busyId, setBusyId] = useState('')

  async function load() { setData(await api<StudentOwnPath>('/adaptive/me')) }
  useEffect(() => { void load().catch((error: Error) => setMessage(error.message)) }, [])

  async function complete(step: PathStep) {
    setBusyId(step.id); setMessage('')
    try {
      await api(`/adaptive/steps/${step.id}/complete`, { method: 'POST', body: JSON.stringify({ evidence_count: 1, notes: 'Etapa marcada como concluída pelo estudante.' }) })
      setMessage('Etapa concluída. O próximo passo foi liberado quando aplicável.')
      await load()
    } catch (error) { setMessage((error as Error).message) } finally { setBusyId('') }
  }

  return (
    <section>
      <header className="page-header student-path-header"><div><span className="eyebrow">MINHA JORNADA</span><h1>Minha trilha de aprendizagem</h1><p>Veja seu objetivo, as atividades disponíveis e as próximas revisões. Seu progresso não é comparado publicamente com colegas.</p></div></header>
      {message ? <div className="inline-message">{message}</div> : null}
      {data ? <div className="privacy-note">{data.explanation}</div> : null}

      <article className="panel"><h2>Meu mapa de progresso</h2><div className="student-skill-strip">{data?.skill_states.slice(0, 8).map((state) => <article key={state.id}><span>{state.dimension_code}</span><strong>{pct(state.mastery_score)}</strong><small>{state.mastery_level.replaceAll('_', ' ')}</small></article>)}{!data?.skill_states.length ? <p className="muted">Seu mapa será exibido após as primeiras atividades avaliadas.</p> : null}</div></article>

      <div className="student-path-list">
        {data?.paths.map((path) => <article className="panel" key={path.id}><div className="panel-heading"><div><span className={`status-pill status-${path.status}`}>{path.status}</span><h2>{path.title}</h2><p>{path.goal}</p></div><strong>Meta {pct(path.target_mastery)}</strong></div><div className="student-step-list">{path.steps.map((step) => <article className={`student-step step-${step.status}`} key={step.id}><span className="step-number">{step.position}</span><div><h3>{step.title}</h3><p>{step.description || 'Atividade recomendada pelo professor.'}</p><small>{step.status === 'locked' ? 'Será liberada após a etapa anterior.' : step.status}</small></div>{step.status === 'available' ? <button disabled={busyId === step.id} onClick={() => void complete(step)} type="button">Concluir etapa</button> : null}</article>)}</div></article>)}
        {!data?.paths.length ? <article className="panel"><h2>Nenhuma trilha ativa</h2><p>Seu professor poderá recomendar uma trilha quando houver evidências suficientes.</p></article> : null}
      </div>

      <article className="panel"><h2>Próximas revisões</h2><div className="adaptive-list compact">{data?.reviews.map((review) => <article key={review.id}><div><strong>{review.dimension_code}</strong><p>Revisão {review.review_number} · {new Date(review.scheduled_for).toLocaleDateString('pt-BR')}</p></div></article>)}{!data?.reviews.length ? <p className="muted">Nenhuma revisão programada.</p> : null}</div></article>
    </section>
  )
}
