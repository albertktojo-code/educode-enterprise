import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'
import type { Comic, ComicSummary, LayoutTemplate, PageOrientation } from '../types/comic'
import type { GenerationProject } from '../types/pedagogy'
import type { RagContextSummary } from '../types/rag'

const statusLabels: Record<ComicSummary['status'], string> = {
  draft: 'Rascunho',
  generating: 'Gerando',
  in_review: 'Em revisão',
  approved: 'Aprovada',
  archived: 'Arquivada',
}

function score(value: number) {
  return `${Math.round(value)}%`
}

function defaultTemplate(panelCount: number, templates: LayoutTemplate[]) {
  return templates.find((template) => template.panel_count === panelCount)?.code ?? 'custom'
}

export function ComicsPage() {
  const [comics, setComics] = useState<ComicSummary[]>([])
  const [projects, setProjects] = useState<GenerationProject[]>([])
  const [contexts, setContexts] = useState<RagContextSummary[]>([])
  const [templates, setTemplates] = useState<LayoutTemplate[]>([])
  const [projectId, setProjectId] = useState('')
  const [contextId, setContextId] = useState('')
  const [title, setTitle] = useState('')
  const [pageCount, setPageCount] = useState(4)
  const [panelsByPage, setPanelsByPage] = useState('1,4,3,1')
  const [orientation, setOrientation] = useState<PageOrientation>('portrait')
  const [genre, setGenre] = useState('mystery')
  const [secondaryGenre, setSecondaryGenre] = useState('comedy')
  const [surpriseLevel, setSurpriseLevel] = useState(4)
  const [plotTwists, setPlotTwists] = useState(2)
  const [endingType, setEndingType] = useState('surprising_positive')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function load() {
    const [comicData, projectData, contextData, templateData] = await Promise.all([
      api<ComicSummary[]>('/comics'),
      api<GenerationProject[]>('/generation-projects'),
      api<RagContextSummary[]>('/rag-contexts'),
      api<LayoutTemplate[]>('/comics/layout-templates'),
    ])
    setComics(comicData)
    setProjects(projectData)
    setContexts(contextData.filter((context) => context.status === 'approved'))
    setTemplates(templateData)
    if (!projectId && projectData.length) setProjectId(projectData[0].id)
  }

  useEffect(() => {
    void load().catch((caughtError) => {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao carregar o estúdio de HQs.')
    })
  }, [])

  const projectContexts = useMemo(
    () => contexts.filter((context) => context.generation_project_id === projectId),
    [contexts, projectId],
  )

  useEffect(() => {
    if (!projectContexts.some((context) => context.id === contextId)) {
      setContextId(projectContexts[0]?.id ?? '')
    }
  }, [projectContexts, contextId])

  useEffect(() => {
    const project = projects.find((item) => item.id === projectId)
    if (project && !title.trim()) setTitle(`${project.title} — HQ`)
  }, [projectId, projects, title])

  function parsedPanelCounts() {
    const counts = panelsByPage
      .split(',')
      .map((value) => Number.parseInt(value.trim(), 10))
      .filter((value) => Number.isFinite(value))
    return Array.from({ length: pageCount }, (_, index) => {
      const value = counts[index] ?? counts[counts.length - 1] ?? 4
      return Math.min(8, Math.max(1, value))
    })
  }

  async function generate(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setSuccess('')
    try {
      const counts = parsedPanelCounts()
      const comic = await api<Comic>('/comics', {
        method: 'POST',
        body: JSON.stringify({
          generation_project_id: projectId,
          rag_context_id: contextId,
          title,
          page_count: pageCount,
          default_panels_per_page: counts[0] ?? 4,
          page_format: 'a4',
          orientation,
          narrative_profile: {
            main_genre: genre,
            secondary_genre: secondaryGenre,
            emotional_tone: 'surprising',
            humor_level: secondaryGenre === 'comedy' ? 4 : 2,
            suspense_level: genre === 'mystery' ? 4 : 2,
            sadness_level: genre === 'drama' ? 3 : 1,
            surprise_level: surpriseLevel,
            max_plot_twists: plotTwists,
            ending_type: endingType,
            required_elements: [],
            prohibited_elements: [],
          },
          page_layouts: counts.map((panelCount, index) => ({
            page_number: index + 1,
            panel_count: panelCount,
            page_format: 'a4',
            orientation,
            layout_mode: 'recommended',
            layout_template: defaultTemplate(panelCount, templates),
            reading_direction: 'left_to_right',
          })),
        }),
      })
      setSuccess(`HQ “${comic.title}” gerada com ${comic.pages.length} páginas e edição granular.`)
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao gerar a HQ.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <span className="eyebrow">SPRINT 09.1</span>
          <h1>Estúdio de HQs estruturadas</h1>
          <p>
            Gere histórias criativas com continuidade, páginas configuráveis, quadros de formatos
            diferentes, balões editáveis e estrutura pronta para o canvas visual.
          </p>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}

      <form className="panel" onSubmit={generate}>
        <div className="panel-title-row">
          <div>
            <span className="eyebrow">NOVA HQ</span>
            <h2>Direção pedagógica e narrativa</h2>
          </div>
        </div>
        <div className="form-grid studio-three-columns">
          <label>
            Planejamento pedagógico
            <select required value={projectId} onChange={(event) => setProjectId(event.target.value)}>
              <option value="">Selecione</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>{project.title} · {project.topic}</option>
              ))}
            </select>
          </label>
          <label>
            Contexto RAG aprovado
            <select required value={contextId} onChange={(event) => setContextId(event.target.value)}>
              <option value="">Selecione</option>
              {projectContexts.map((context) => (
                <option key={context.id} value={context.id}>{context.title} · {Math.round(context.quality_score)}%</option>
              ))}
            </select>
          </label>
          <label>
            Título
            <input required minLength={3} value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label>
            Quantidade de páginas
            <input type="number" min={1} max={20} value={pageCount} onChange={(event) => setPageCount(Number(event.target.value))} />
          </label>
          <label>
            Quadros por página
            <input value={panelsByPage} onChange={(event) => setPanelsByPage(event.target.value)} placeholder="1,4,3,1" />
            <small>Informe de 1 a 8 quadros por página, separados por vírgula.</small>
          </label>
          <label>
            Orientação
            <select value={orientation} onChange={(event) => setOrientation(event.target.value as PageOrientation)}>
              <option value="portrait">Vertical</option>
              <option value="landscape">Horizontal</option>
            </select>
          </label>
          <label>
            Gênero principal
            <select value={genre} onChange={(event) => setGenre(event.target.value)}>
              <option value="mystery">Mistério</option>
              <option value="adventure">Aventura</option>
              <option value="comedy">Comédia</option>
              <option value="drama">Drama</option>
              <option value="science_fiction">Ficção científica</option>
              <option value="fantasy">Fantasia</option>
            </select>
          </label>
          <label>
            Gênero secundário
            <select value={secondaryGenre} onChange={(event) => setSecondaryGenre(event.target.value)}>
              <option value="comedy">Engraçada</option>
              <option value="emotional">Emocionante</option>
              <option value="drama">Triste/dramática</option>
              <option value="suspense">Suspense</option>
              <option value="inspiring">Inspiradora</option>
            </select>
          </label>
          <label>
            Nível de surpresa: {surpriseLevel}
            <input type="range" min={0} max={5} value={surpriseLevel} onChange={(event) => setSurpriseLevel(Number(event.target.value))} />
          </label>
          <label>
            Máximo de plot twists
            <input type="number" min={0} max={4} value={plotTwists} onChange={(event) => setPlotTwists(Number(event.target.value))} />
          </label>
          <label>
            Tipo de final
            <select value={endingType} onChange={(event) => setEndingType(event.target.value)}>
              <option value="surprising_positive">Positivo e surpreendente</option>
              <option value="emotional">Emocionante</option>
              <option value="funny">Engraçado</option>
              <option value="open_hook">Aberto com gancho</option>
              <option value="bittersweet">Agridoce</option>
            </select>
          </label>
        </div>
        <button className="primary" type="submit" disabled={busy || !contextId || !projectId}>
          {busy ? 'Gerando páginas e quadros…' : 'Gerar HQ estruturada'}
        </button>
      </form>

      <section className="panel">
        <div className="panel-title-row">
          <div>
            <span className="eyebrow">BIBLIOTECA</span>
            <h2>HQs geradas</h2>
          </div>
        </div>
        <div className="comic-library-grid">
          {comics.map((comic) => (
            <article className="comic-library-card" key={comic.id}>
              <div className="comic-cover-placeholder">
                <span>{comic.page_count} páginas</span>
                <strong>{comic.panel_count}</strong>
                <small>quadros editáveis</small>
              </div>
              <div className="comic-card-copy">
                <span className={`status-chip ${comic.status.replaceAll('_', '-')}`}>{statusLabels[comic.status]}</span>
                <h3>{comic.title}</h3>
                <p>{comic.synopsis}</p>
                <div className="score-grid compact">
                  <span>Continuidade <strong>{score(comic.continuity_score)}</strong></span>
                  <span>Pedagogia <strong>{score(comic.pedagogical_score)}</strong></span>
                  <span>Versão <strong>v{comic.current_version}</strong></span>
                </div>
                <div className="comic-card-actions">
                  <Link className="secondary-button" to={`/hqs/${comic.id}/preview`}>Pré-visualizar</Link>
                  <Link className="secondary-button" to={`/storyboards/${comic.id}`}>Storyboard</Link>
                  <Link className="secondary-button" to={`/hqs/${comic.id}`}>Revisão granular</Link>
                  <Link className="primary-link" to={`/canvas/${comic.id}`}>Abrir canvas visual</Link>
                </div>
              </div>
            </article>
          ))}
          {!comics.length ? <p>Nenhuma HQ foi gerada até agora.</p> : null}
        </div>
      </section>
    </section>
  )
}
