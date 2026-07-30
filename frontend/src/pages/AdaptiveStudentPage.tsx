import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../lib/api'
import type { StudentAdaptiveSummary } from '../types/adaptive'

const levelLabels: Record<string, string> = {
  not_assessed: 'Não avaliado',
  insufficient_evidence: 'Evidências insuficientes',
  initial: 'Inicial',
  developing: 'Em desenvolvimento',
  adequate: 'Adequado',
  advanced: 'Avançado',
}

function percentage(value: number) { return `${(value * 100).toFixed(1)}%` }

export function AdaptiveStudentPage() {
  const { studentId } = useParams()
  const [summary, setSummary] = useState<StudentAdaptiveSummary | null>(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    if (!studentId) return
    setSummary(await api<StudentAdaptiveSummary>(`/adaptive/students/${studentId}`))
  }

  useEffect(() => { void load().catch((error: Error) => setMessage(error.message)) }, [studentId])

  async function generate() {
    if (!studentId) return
    setBusy(true); setMessage('')
    try {
      const result = await api<Array<{ id: string }>>('/adaptive/recommendations/generate', {
        method: 'POST',
        body: JSON.stringify({ student_id: studentId, maximum_recommendations: 5 }),
      })
      setMessage(`${result.length} nova(s) recomendação(ões) criada(s) para revisão.`)
      await load()
    } catch (error) { setMessage((error as Error).message) } finally { setBusy(false) }
  }

  return (
    <section>
      <header className="page-header">
        <div><span className="eyebrow">PERFIL ADAPTATIVO</span><h1>Mapa individual de domínio</h1><p>Cada indicador mostra o domínio estimado, a confiança, a tendência e a origem das evidências.</p></div>
        <div className="button-row"><button className="primary-button" disabled={busy} onClick={() => void generate()} type="button">{busy ? 'Gerando...' : 'Gerar recomendações'}</button><Link className="secondary-button" to="/adaptativo/recomendacoes">Revisar recomendações</Link></div>
      </header>
      {message ? <div className="inline-message">{message}</div> : null}

      <div className="analytics-card-grid">
        <article className="metric-card"><span>Dimensões avaliadas</span><strong>{summary?.skill_states.length ?? 0}</strong><small>BNCC e Pensamento Computacional</small></article>
        <article className="metric-card"><span>Trilhas ativas</span><strong>{summary?.active_paths ?? 0}</strong><small>aprovadas pelo professor</small></article>
        <article className="metric-card metric-attention"><span>Recomendações pendentes</span><strong>{summary?.pending_recommendations ?? 0}</strong><small>aguardando decisão humana</small></article>
        <article className="metric-card"><span>Revisões futuras</span><strong>{summary?.upcoming_reviews ?? 0}</strong><small>revisão espaçada</small></article>
      </div>

      <article className="panel">
        <div className="panel-heading"><div><h2>Habilidades e pilares</h2><p>Domínio calculado por regras determinísticas e versionadas.</p></div></div>
        <div className="skill-map-grid">
          {summary?.skill_states.map((state) => (
            <article className={`skill-state level-${state.mastery_level}`} key={state.id}>
              <div className="skill-state-head"><span>{state.dimension_type}</span><strong>{state.dimension_code}</strong></div>
              <div className="mastery-score"><b>{percentage(state.mastery_score)}</b><span>{levelLabels[state.mastery_level] ?? state.mastery_level}</span></div>
              <div className="mastery-track"><span style={{ width: `${state.mastery_score * 100}%` }} /></div>
              <dl><div><dt>Confiança</dt><dd>{state.confidence_level} ({percentage(state.confidence_score)})</dd></div><div><dt>Evidências</dt><dd>{state.evidence_count}</dd></div><div><dt>Tendência</dt><dd>{state.trend}</dd></div></dl>
              <p>{state.calculation_explanation}</p>
            </article>
          ))}
          {!summary?.skill_states.length ? <p className="muted">Nenhuma evidência calculada. Use “Atualizar e recomendar” no painel adaptativo.</p> : null}
        </div>
      </article>

      <div className="analytics-two-columns">
        <article className="panel"><h2>Prioridades atuais</h2><div className="adaptive-list compact">{summary?.weakest_dimensions.map((state) => <article key={state.id}><div><strong>{state.dimension_code}</strong><p>{percentage(state.mastery_score)} · {state.evidence_count} evidências · confiança {state.confidence_level}</p></div></article>)}</div></article>
        <article className="panel"><h2>Pontos fortes</h2><div className="adaptive-list compact">{summary?.strongest_dimensions.map((state) => <article key={state.id}><div><strong>{state.dimension_code}</strong><p>{percentage(state.mastery_score)} · tendência {state.trend}</p></div></article>)}</div></article>
      </div>
    </section>
  )
}
