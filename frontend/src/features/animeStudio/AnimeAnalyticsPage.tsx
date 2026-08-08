import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { EmptyState } from '../../components/EmptyState'
import { LoadingState } from '../../components/LoadingState'
import { animeStudioApi } from './api'
import type { AnimeAnalytics } from './types'
import './analyticsStyles.css'

function formatPercentage(value: number | null): string {
  return value === null ? 'Sem dados' : `${value.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
}

function formatTimestamp(milliseconds: number): string {
  const totalSeconds = Math.round(milliseconds / 1000)
  return `${Math.floor(totalSeconds / 60)}:${String(totalSeconds % 60).padStart(2, '0')}`
}

export function AnimeAnalyticsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [analytics, setAnalytics] = useState<AnimeAnalytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!projectId) {
      setError('Projeto audiovisual não informado.')
      setLoading(false)
      return
    }
    animeStudioApi.getAnalytics(projectId)
      .then(setAnalytics)
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false))
  }, [projectId])

  return (
    <section className="anime-analytics-shell">
      <header className="anime-analytics-hero">
        <div>
          <span>EDUCODE ANALYTICS · AUDIOVISUAL</span>
          <h1>{analytics?.title ?? 'Desempenho do anime'}</h1>
          <p>Métricas agregadas de alcance, conclusão e aprendizagem nos checkpoints.</p>
        </div>
        <Link to="/anime-studio">Voltar ao Studio</Link>
      </header>

      {error ? <div className="anime-analytics-alert" role="alert">{error}</div> : null}
      {loading ? <LoadingState label="Calculando desempenho audiovisual" rows={4} /> : null}

      {!loading && analytics ? <>
        <div className="anime-analytics-cards" aria-label="Resumo do vídeo">
          <article><span>Reproduções</span><strong>{analytics.play_count}</strong></article>
          <article><span>Estudantes alcançados</span><strong>{analytics.viewer_count}</strong></article>
          <article><span>Conclusão do vídeo</span><strong>{formatPercentage(analytics.video_completion_rate)}</strong></article>
          <article><span>Avanço médio máximo</span><strong>{formatPercentage(analytics.average_max_progress)}</strong></article>
        </div>

        <section className="anime-analytics-panel">
          <header><div><span>FUNIL DE RETENÇÃO</span><h2>Progresso no vídeo</h2></div><small>Publicação {analytics.render_revision ?? '—'}</small></header>
          {analytics.viewer_count ? <ol className="anime-milestone-list">
            {analytics.milestones.map((milestone) => <li key={milestone.percentage}>
              <div><strong>{milestone.percentage}%</strong><span>{milestone.student_count} estudante(s) · {formatPercentage(milestone.reach_rate)}</span></div>
              <progress max={100} value={milestone.reach_rate}>{milestone.reach_rate}%</progress>
            </li>)}
          </ol> : <EmptyState icon="activity" title="Ainda sem reproduções" description="As métricas aparecerão quando estudantes assistirem a esta publicação." />}
        </section>

        <section className="anime-analytics-panel">
          <header><div><span>APRENDIZAGEM INTEGRADA</span><h2>Desempenho por checkpoint</h2></div></header>
          {analytics.checkpoints.length ? <div className="anime-checkpoint-analytics-grid">
            {analytics.checkpoints.map((checkpoint) => <article key={checkpoint.checkpoint_id}>
              <div><time>{formatTimestamp(checkpoint.timestamp_ms)}</time><h3>{checkpoint.label}</h3></div>
              <dl>
                <div><dt>Chegaram</dt><dd>{checkpoint.reached_students}</dd></div>
                <div><dt>Concluíram</dt><dd>{checkpoint.completed_students}</dd></div>
                <div><dt>Taxa de conclusão</dt><dd>{formatPercentage(checkpoint.completion_rate)}</dd></div>
                <div><dt>Desempenho médio</dt><dd>{formatPercentage(checkpoint.average_percentage)}</dd></div>
              </dl>
            </article>)}
          </div> : <EmptyState icon="folder" title="Sem checkpoints publicados" description="Adicione atividades ao vídeo para acompanhar o desempenho pedagógico por trecho." />}
        </section>

        {analytics.data_quality_notes.length ? <aside className="anime-data-quality" aria-label="Observações sobre os dados">
          <strong>Sobre estes dados</strong>
          <ul>{analytics.data_quality_notes.map((note) => <li key={note}>{note}</li>)}</ul>
        </aside> : null}
      </> : null}
    </section>
  )
}
