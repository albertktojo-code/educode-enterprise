import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { ComicPreviewSurface } from '../components/ComicPreviewSurface'
import { api } from '../lib/api'
import type { Comic, ComicPanel, PreviewReviewStatus, ReviewSpecialty } from '../types/comic'
import type { PreviewValidation, VersionComparison } from '../types/preview'

type PreviewMode = 'student' | 'teacher' | 'print'
type ViewMode = 'single' | 'spread' | 'scroll' | 'mobile'

const statusLabels: Record<PreviewReviewStatus, string> = {
  not_reviewed: 'Não revisado',
  in_review: 'Em revisão',
  changes_requested: 'Correção solicitada',
  approved: 'Aprovado',
  locked: 'Aprovado e bloqueado',
}

export function ComicPreviewPage() {
  const { comicId = '' } = useParams()
  const [comic, setComic] = useState<Comic | null>(null)
  const [validation, setValidation] = useState<PreviewValidation | null>(null)
  const [pageIndex, setPageIndex] = useState(0)
  const [selectedPanel, setSelectedPanel] = useState<ComicPanel | null>(null)
  const [commentAnchor, setCommentAnchor] = useState<{ x: number; y: number } | null>(null)
  const [previewMode, setPreviewMode] = useState<PreviewMode>('teacher')
  const [viewMode, setViewMode] = useState<ViewMode>('single')
  const [reviewNotes, setReviewNotes] = useState('')
  const [comment, setComment] = useState('')
  const [commentSpecialty, setCommentSpecialty] = useState<ReviewSpecialty>('visual')
  const [comparison, setComparison] = useState<VersionComparison | null>(null)
  const [fromVersion, setFromVersion] = useState(1)
  const [toVersion, setToVersion] = useState(1)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    const [comicData, validationData] = await Promise.all([
      api<Comic>(`/comics/${comicId}`),
      api<PreviewValidation>(`/comics/${comicId}/preview-validation`),
    ])
    setComic(comicData)
    setValidation(validationData)
    setToVersion(comicData.current_version)
    setFromVersion(Math.max(1, comicData.current_version - 1))
    setSelectedPanel((current) => current ?? comicData.pages[0]?.panels[0] ?? null)
  }

  useEffect(() => {
    void load().catch((caughtError) => setError(caughtError instanceof Error ? caughtError.message : 'Falha ao abrir prévia.'))
  }, [comicId])

  const currentPage = comic?.pages[pageIndex] ?? null
  const spreadPages = useMemo(() => {
    if (!comic || !currentPage) return []
    if (viewMode !== 'spread') return [currentPage]
    const second = comic.pages[pageIndex + 1]
    return second ? [currentPage, second] : [currentPage]
  }, [comic, currentPage, pageIndex, viewMode])

  async function reviewTarget(target: 'page' | 'panel', status: PreviewReviewStatus, lock = false) {
    if (!comic || !currentPage) return
    const targetId = target === 'page' ? currentPage.id : selectedPanel?.id
    if (!targetId) return
    setBusy(true)
    setError('')
    try {
      await api(`/comics/${comic.id}/${target === 'page' ? 'pages' : 'panels'}/${targetId}/preview-review`, {
        method: 'POST',
        body: JSON.stringify({ status, notes: reviewNotes || null, lock_after_approval: lock }),
      })
      setReviewNotes('')
      setSuccess(`${target === 'page' ? 'Página' : 'Quadro'} atualizado: ${statusLabels[lock ? 'locked' : status]}.`)
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao registrar revisão.')
    } finally {
      setBusy(false)
    }
  }

  async function createComment(event: FormEvent) {
    event.preventDefault()
    if (!comic || !comment.trim()) return
    setBusy(true)
    try {
      await api(`/comics/${comic.id}/comments`, {
        method: 'POST',
        body: JSON.stringify({
          specialty: commentSpecialty,
          body: comment,
          page_id: currentPage?.id ?? null,
          panel_id: selectedPanel?.id ?? null,
          priority: 'normal',
          anchor_x: commentAnchor?.x ?? null,
          anchor_y: commentAnchor?.y ?? null,
        }),
      })
      setComment('')
      setCommentAnchor(null)
      setSuccess('Comentário registrado na prévia.')
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao comentar.')
    } finally {
      setBusy(false)
    }
  }

  async function compareVersions() {
    setError('')
    try {
      const result = await api<VersionComparison>(`/comics/${comicId}/version-comparison?from_version=${fromVersion}&to_version=${toVersion}`)
      setComparison(result)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao comparar versões.')
    }
  }

  if (!comic || !currentPage) return <div className="panel">{error || 'Carregando prévia…'}</div>

  const pagesToRender = viewMode === 'scroll' ? comic.pages : spreadPages

  return (
    <section className={`preview-review-page mode-${previewMode} view-${viewMode}`}>
      <header className="preview-toolbar">
        <div>
          <span className="eyebrow">PRÉ-VISUALIZAÇÃO DO PROFESSOR</span>
          <h1>{comic.title}</h1>
          <small>Versão {comic.current_version} · {comic.pages.length} páginas</small>
        </div>
        <div className="preview-toolbar-actions">
          <Link to={`/storyboards/${comic.id}`}>Storyboard</Link>
          <Link to={`/hqs/${comic.id}`}>Revisão granular</Link>
          <Link to={`/canvas/${comic.id}?page=${currentPage.id}${selectedPanel ? `&panel=${selectedPanel.id}` : ''}`}>Abrir no canvas</Link>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}

      <div className="preview-control-bar">
        <div>
          <strong>Modo</strong>
          {(['student', 'teacher', 'print'] as PreviewMode[]).map((mode) => (
            <button className={previewMode === mode ? 'active' : ''} key={mode} onClick={() => setPreviewMode(mode)} type="button">
              {mode === 'student' ? 'Estudante' : mode === 'teacher' ? 'Professor' : 'Impressão'}
            </button>
          ))}
        </div>
        <div>
          <strong>Visualização</strong>
          {(['single', 'spread', 'scroll', 'mobile'] as ViewMode[]).map((mode) => (
            <button className={viewMode === mode ? 'active' : ''} key={mode} onClick={() => setViewMode(mode)} type="button">
              {mode === 'single' ? 'Página' : mode === 'spread' ? 'Duas páginas' : mode === 'scroll' ? 'Rolagem' : 'Celular'}
            </button>
          ))}
        </div>
      </div>

      <div className="preview-workspace">
        <aside className="preview-thumbnails">
          {comic.pages.map((page, index) => (
            <button className={index === pageIndex ? 'active' : ''} key={page.id} onClick={() => { setPageIndex(index); setSelectedPanel(page.panels[0] ?? null) }} type="button">
              <span>Página {page.page_number}</span>
              <small>{statusLabels[page.preview_review_status]}</small>
              <ComicPreviewSurface compact page={page} />
            </button>
          ))}
        </aside>

        <main className={`preview-stage ${viewMode === 'mobile' ? 'mobile' : ''}`}>
          {pagesToRender.map((page) => (
            <ComicPreviewSurface
              key={page.id}
              page={page}
              selectedPanelId={selectedPanel?.id}
              showTeacherOverlay={previewMode === 'teacher'}
              onSelectPanel={(panel, point) => {
                setSelectedPanel(panel)
                setCommentAnchor(point)
                const index = comic.pages.findIndex((item) => item.id === page.id)
                if (index >= 0) setPageIndex(index)
              }}
            />
          ))}
        </main>

        {previewMode === 'teacher' ? (
          <aside className="preview-review-panel">
            <section>
              <h2>Revisão atual</h2>
              <p><strong>Página:</strong> {statusLabels[currentPage.preview_review_status]}</p>
              <p><strong>Quadro:</strong> {selectedPanel ? statusLabels[selectedPanel.preview_review_status] : 'Selecione um quadro'}</p>
              <textarea placeholder="Observações da revisão" value={reviewNotes} onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setReviewNotes(event.target.value)} />
              <div className="review-action-grid">
                <button disabled={busy} onClick={() => void reviewTarget('page', 'approved')} type="button">Aprovar página</button>
                <button disabled={busy} onClick={() => void reviewTarget('page', 'approved', true)} type="button">Aprovar e bloquear</button>
                <button disabled={busy} onClick={() => void reviewTarget('page', 'changes_requested')} type="button">Solicitar correção</button>
                <button disabled={busy || !selectedPanel} onClick={() => void reviewTarget('panel', 'approved')} type="button">Aprovar quadro</button>
              </div>
            </section>

            <section>
              <h2>Comentário</h2>
              <form onSubmit={createComment}>
                <select value={commentSpecialty} onChange={(event: ChangeEvent<HTMLSelectElement>) => setCommentSpecialty(event.target.value as ReviewSpecialty)}>
                  <option value="narrative">Narrativa</option>
                  <option value="pedagogical">Pedagógica</option>
                  <option value="visual">Visual</option>
                  <option value="accessibility">Acessibilidade</option>
                </select>
                {commentAnchor ? (
                  <small>Ponto marcado no quadro: {commentAnchor.x.toFixed(1)}% × {commentAnchor.y.toFixed(1)}%</small>
                ) : (
                  <small>Clique no ponto do quadro que deseja comentar.</small>
                )}
                <textarea required minLength={3} placeholder="Descreva a correção necessária" value={comment} onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setComment(event.target.value)} />
                <button className="secondary-button" disabled={busy} type="submit">Adicionar comentário</button>
              </form>
            </section>

            {validation ? (
              <section>
                <h2>Prontidão</h2>
                <div className={`preview-readiness status-${validation.status}`}>
                  <strong>{validation.review_coverage_percent}% revisado</strong>
                  <span>{validation.error_count} erros · {validation.warning_count} alertas</span>
                </div>
                <ul className="preview-checklist">
                  {validation.checklist.map((item) => <li className={item.passed ? 'passed' : ''} key={item.code}>{item.passed ? '✓' : '○'} {item.label}</li>)}
                </ul>
                {validation.findings.slice(0, 5).map((finding) => <p className={`preview-finding ${finding.severity}`} key={`${finding.code}-${finding.message}`}>{finding.message}</p>)}
              </section>
            ) : null}

            <section>
              <h2>Comparar versões</h2>
              <div className="version-compare-controls">
                <input min={1} max={comic.current_version} type="number" value={fromVersion} onChange={(event: ChangeEvent<HTMLInputElement>) => setFromVersion(Number(event.target.value))} />
                <span>→</span>
                <input min={1} max={comic.current_version} type="number" value={toVersion} onChange={(event: ChangeEvent<HTMLInputElement>) => setToVersion(Number(event.target.value))} />
                <button onClick={() => void compareVersions()} type="button">Comparar</button>
              </div>
              {comparison ? (
                <div className="version-comparison-result">
                  <strong>{comparison.changed_pages.length} página(s) alterada(s)</strong>
                  <small>Campos gerais: {comparison.top_level_changes.join(', ') || 'nenhum'}</small>
                  {comparison.changed_pages.map((page) => (
                    <div key={page.page_id}>
                      <span>Página {page.page_number ?? '?'}: {page.status}</span>
                      {page.panel_changes.map((panel) => (
                        <small key={panel.panel_id}>Quadro: {panel.status} · {panel.changed_fields.join(', ') || 'sem campos alterados'}</small>
                      ))}
                    </div>
                  ))}
                </div>
              ) : null}
            </section>
          </aside>
        ) : null}
      </div>
    </section>
  )
}
