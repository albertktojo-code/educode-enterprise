import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../lib/api'
import type { Storyboard, StoryboardScene } from '../types/preview'

const plotLabels: Record<string, string> = {
  opening: 'Abertura',
  problem: 'Problema',
  clue: 'Pista',
  false_solution: 'Falsa solução',
  plot_twist: 'Reviravolta',
  resolution: 'Resolução',
  development: 'Desenvolvimento',
}

export function StoryboardPage() {
  const { comicId = '' } = useParams()
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null)
  const [selectedPage, setSelectedPage] = useState<number | 'all'>('all')
  const [error, setError] = useState('')

  useEffect(() => {
    void api<Storyboard>(`/comics/${comicId}/storyboard`)
      .then(setStoryboard)
      .catch((caughtError) => setError(caughtError instanceof Error ? caughtError.message : 'Falha ao abrir storyboard.'))
  }, [comicId])

  const scenes = useMemo(
    () => storyboard?.scenes.filter((scene) => selectedPage === 'all' || scene.page_number === selectedPage) ?? [],
    [selectedPage, storyboard],
  )

  if (error) return <div className="alert error">{error}</div>
  if (!storyboard) return <div className="panel">Carregando storyboard…</div>

  const pages = Array.from(new Set(storyboard.scenes.map((scene) => scene.page_number)))

  return (
    <section className="page-stack storyboard-page">
      <header className="page-header storyboard-header">
        <div>
          <span className="eyebrow">SPRINT 09.1 · STORYBOARD</span>
          <h1>{storyboard.title}</h1>
          <p>{storyboard.scene_count} cenas · {storyboard.page_count} páginas · aproximadamente {storyboard.estimated_duration_seconds}s em versão animada.</p>
        </div>
        <div className="card-actions">
          <Link className="secondary-button" to={`/hqs/${comicId}/preview`}>Abrir prévia</Link>
          <Link className="secondary-button" to={`/hqs/${comicId}`}>Revisão granular</Link>
          <Link className="primary-link" to={`/canvas/${comicId}`}>Abrir canvas</Link>
        </div>
      </header>

      <section className="panel storyboard-summary">
        <div>
          <h2>Linha emocional</h2>
          <div className="emotional-arc">
            {storyboard.emotional_arc.map((emotion, index) => <span key={`${emotion}-${index}`}>{emotion}</span>)}
          </div>
        </div>
        <div>
          <h2>Pistas e reviravoltas</h2>
          <div className="plot-point-list">
            {storyboard.plot_points.map((point) => (
              <span key={`${point.sequence_number}-${point.type}`}>
                P{point.page_number}/Q{point.panel_number} · {plotLabels[point.type] || point.type}
              </span>
            ))}
          </div>
        </div>
      </section>

      <div className="storyboard-filter-bar">
        <button className={selectedPage === 'all' ? 'active' : ''} onClick={() => setSelectedPage('all')} type="button">Todas</button>
        {pages.map((page) => (
          <button className={selectedPage === page ? 'active' : ''} key={page} onClick={() => setSelectedPage(page)} type="button">Página {page}</button>
        ))}
      </div>

      <section className="storyboard-grid">
        {scenes.map((scene: StoryboardScene) => (
          <article className="storyboard-card" key={scene.panel_id}>
            <div className="storyboard-card-head">
              <span>Cena {scene.sequence_number}</span>
              <strong>P{scene.page_number} · Q{scene.panel_number}</strong>
              <span className={`status-chip ${scene.review_status}`}>{scene.review_status.replaceAll('_', ' ')}</span>
            </div>
            <div className="storyboard-frame">
              {scene.image_asset_path ? <img alt={scene.alt_text || ''} src={scene.image_asset_path} /> : <p>{scene.scene_summary}</p>}
            </div>
            <dl className="storyboard-meta">
              <div><dt>Função</dt><dd>{plotLabels[scene.plot_function] || scene.plot_function}</dd></div>
              <div><dt>Plano</dt><dd>{scene.shot_type}</dd></div>
              <div><dt>Emoção</dt><dd>{scene.emotion}</dd></div>
              <div><dt>Ritmo</dt><dd>{scene.pacing}</dd></div>
              <div><dt>Transição</dt><dd>{scene.transition}</dd></div>
              <div><dt>Duração</dt><dd>{scene.estimated_duration_seconds}s</dd></div>
            </dl>
            <div className="storyboard-goals">
              <p><strong>Narrativa:</strong> {scene.narrative_goal}</p>
              <p><strong>Pedagógica:</strong> {scene.pedagogical_goal}</p>
              {scene.ct_pillar_codes.length ? <small>PC: {scene.ct_pillar_codes.join(', ')}</small> : null}
            </div>
            <div className="storyboard-dialogue">
              {scene.dialogue.map((line) => (
                <blockquote key={line.balloon_id}><strong>{line.speaker}</strong>{line.text}</blockquote>
              ))}
            </div>
            <footer>
              <small>Gancho: {scene.next_panel_hook || 'Encerramento da cena'}</small>
              <Link to={`/canvas/${comicId}?page=${scene.page_id}&panel=${scene.panel_id}`}>Editar esta cena</Link>
            </footer>
          </article>
        ))}
      </section>
    </section>
  )
}
