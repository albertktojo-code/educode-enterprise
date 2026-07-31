import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { ComicCover } from '../components/ComicCover'
import { EmptyState } from '../components/EmptyState'
import { LoadingState } from '../components/LoadingState'
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
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | ComicSummary['status']>('all')

  async function load() {
    setLoading(true)
    try {
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
    } finally {
      setLoading(false)
    }
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

  const filteredComics = useMemo(() => {
    const normalizedSearch = search.trim().toLocaleLowerCase('pt-BR')
    return comics.filter((comic) => {
      const matchesStatus = statusFilter === 'all' || comic.status === statusFilter
      const matchesSearch =
        !normalizedSearch ||
        comic.title.toLocaleLowerCase('pt-BR').includes(normalizedSearch) ||
        comic.synopsis.toLocaleLowerCase('pt-BR').includes(normalizedSearch)
      return matchesStatus && matchesSearch
    })
  }, [comics, search, statusFilter])

  const catalogSummary = useMemo(
    () => ({
      total: comics.length,
      review: comics.filter((comic) => comic.status === 'in_review').length,
      approved: comics.filter((comic) => comic.status === 'approved').length,
    }),
    [comics],
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
    <section className="page-stack hq-catalog-page">
      <header className="page-header hq-catalog-hero">
        <div>
          <span className="eyebrow">ESTÚDIO EDUCODE</span>
          <h1>Minhas HQs</h1>
          <p>
            Crie, organize e revise histórias pedagógicas em um espaço visual pensado para o seu fluxo.
          </p>
        </div>
        <a className="primary-link" href="#nova-hq">Criar nova HQ</a>
      </header>

      <div className="hq-catalog-summary" aria-label="Resumo das minhas HQs">
        <div><strong>{catalogSummary.total}</strong><span>HQs no estúdio</span></div>
        <div><strong>{catalogSummary.review}</strong><span>em revisão</span></div>
        <div><strong>{catalogSummary.approved}</strong><span>aprovadas</span></div>
      </div>

      {error ? <div className="alert error" role="alert">{error}</div> : null}
      {success ? <div className="alert success" role="status">{success}</div> : null}

      <form className="panel hq-create-panel" id="nova-hq" onSubmit={generate}>
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

      <section className="panel hq-catalog-panel" aria-labelledby="hq-library-title">
        <div className="panel-title-row">
          <div>
            <span className="eyebrow">BIBLIOTECA</span>
            <h2 id="hq-library-title">HQs geradas</h2>
            <p>Continue do ponto em que parou ou abra uma etapa específica da produção.</p>
          </div>
          <span className="hq-result-count" aria-live="polite">
            {filteredComics.length} {filteredComics.length === 1 ? 'resultado' : 'resultados'}
          </span>
        </div>

        <div className="hq-catalog-toolbar" role="search">
          <label className="hq-search-field">
            <span className="sr-only">Buscar HQ</span>
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="m20 20-4.4-4.4m2.15-5.35a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z" />
            </svg>
            <input
              type="search"
              placeholder="Buscar por título ou assunto"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <label>
            <span className="sr-only">Filtrar HQs por status</span>
            <select
              value={statusFilter}
              onChange={(event) =>
                setStatusFilter(event.target.value as 'all' | ComicSummary['status'])
              }
            >
              <option value="all">Todos os status</option>
              <option value="draft">Rascunhos</option>
              <option value="generating">Em geração</option>
              <option value="in_review">Em revisão</option>
              <option value="approved">Aprovadas</option>
              <option value="archived">Arquivadas</option>
            </select>
          </label>
        </div>

        {loading ? <LoadingState label="Carregando suas HQs" rows={3} /> : null}

        {!loading && filteredComics.length ? (
          <div className="comic-library-grid">
            {filteredComics.map((comic) => (
              <article className="comic-library-card" key={comic.id}>
                <Link
                  className="comic-card-cover-link"
                  to={`/hqs/${comic.id}/preview`}
                  aria-label={`Pré-visualizar ${comic.title}`}
                >
                  <ComicCover
                    title={comic.title}
                    eyebrow={`${comic.page_count} páginas`}
                    footer={`${comic.panel_count} quadros · v${comic.current_version}`}
                    seed={comic.id}
                  />
                </Link>
                <div className="comic-card-copy">
                  <div className="comic-card-heading">
                    <span className={`status-chip ${comic.status.replaceAll('_', '-')}`}>
                      {statusLabels[comic.status]}
                    </span>
                    <span>
                      Atualizada em {new Intl.DateTimeFormat('pt-BR').format(new Date(comic.updated_at))}
                    </span>
                  </div>
                  <h3>{comic.title}</h3>
                  <p>{comic.synopsis || 'Uma HQ pedagógica criada no EduCode.'}</p>
                  <div className="score-grid compact" aria-label={`Indicadores de ${comic.title}`}>
                    <span>Continuidade <strong>{score(comic.continuity_score)}</strong></span>
                    <span>Pedagogia <strong>{score(comic.pedagogical_score)}</strong></span>
                    <span>Versão <strong>v{comic.current_version}</strong></span>
                  </div>
                  <div className="comic-card-actions">
                    <Link className="primary-link" to={`/canvas/${comic.id}`}>Abrir no canvas</Link>
                    <Link className="secondary-button" to={`/hqs/${comic.id}`}>Revisar</Link>
                    <Link className="text-link" to={`/storyboards/${comic.id}`}>Storyboard</Link>
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : null}

        {!loading && !filteredComics.length ? (
          <EmptyState
            icon={comics.length ? 'search' : 'folder'}
            title={comics.length ? 'Nenhuma HQ corresponde aos filtros' : 'Sua primeira história começa aqui'}
            description={
              comics.length
                ? 'Ajuste a busca ou o status para reencontrar uma HQ do seu estúdio.'
                : 'Defina o planejamento, o contexto pedagógico e a narrativa para criar sua primeira HQ.'
            }
            action={
              comics.length ? (
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => {
                    setSearch('')
                    setStatusFilter('all')
                  }}
                >
                  Limpar filtros
                </button>
              ) : (
                <a className="primary-link" href="#nova-hq">Começar uma HQ</a>
              )
            }
          />
        ) : null}
      </section>
    </section>
  )
}
