import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../lib/api'
import type { Comic, ComicBalloon, ComicPanel } from '../types/comic'

type Selection =
  | { kind: 'panel'; id: string }
  | { kind: 'balloon'; id: string }
  | null

type DragState = {
  kind: 'panel' | 'balloon' | 'resize-panel' | 'resize-balloon'
  id: string
  startX: number
  startY: number
  originalX: number
  originalY: number
  originalWidth: number
  originalHeight: number
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

export function TeacherCanvasPage() {
  const { comicId } = useParams()
  const [comic, setComic] = useState<Comic | null>(null)
  const [selectedPageId, setSelectedPageId] = useState<string | null>(null)
  const [selection, setSelection] = useState<Selection>(null)
  const [zoom, setZoom] = useState(0.78)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [dirty, setDirty] = useState(false)
  const dragRef = useRef<DragState | null>(null)
  const pageRef = useRef<HTMLDivElement | null>(null)

  async function load() {
    if (!comicId) return
    const data = await api<Comic>(`/comics/${comicId}`)
    setComic(data)
    setSelectedPageId((current) => current ?? data.pages[0]?.id ?? null)
  }

  useEffect(() => {
    void load().catch((error: Error) => setMessage(error.message))
  }, [comicId])

  const selectedPage = useMemo(
    () => comic?.pages.find((page) => page.id === selectedPageId) ?? null,
    [comic, selectedPageId],
  )
  const selectedPanel = useMemo(() => {
    if (!selectedPage || selection?.kind !== 'panel') return null
    return selectedPage.panels.find((panel) => panel.id === selection.id) ?? null
  }, [selectedPage, selection])
  const selectedBalloon = useMemo(() => {
    if (!selectedPage || selection?.kind !== 'balloon') return null
    return selectedPage.panels.flatMap((panel) => panel.balloons).find((balloon) => balloon.id === selection.id) ?? null
  }, [selectedPage, selection])

  function updatePanel(panelId: string, patch: Partial<ComicPanel>) {
    setComic((current) => current ? {
      ...current,
      pages: current.pages.map((page) => ({
        ...page,
        panels: page.panels.map((panel) => panel.id === panelId ? { ...panel, ...patch } : panel),
      })),
    } : current)
    setDirty(true)
  }

  function updateBalloon(balloonId: string, patch: Partial<ComicBalloon>) {
    setComic((current) => current ? {
      ...current,
      pages: current.pages.map((page) => ({
        ...page,
        panels: page.panels.map((panel) => ({
          ...panel,
          balloons: panel.balloons.map((balloon) => balloon.id === balloonId ? { ...balloon, ...patch } : balloon),
        })),
      })),
    } : current)
    setDirty(true)
  }

  function beginDrag(event: React.PointerEvent, state: DragState) {
    event.stopPropagation()
    event.currentTarget.setPointerCapture(event.pointerId)
    dragRef.current = state
  }

  function moveDrag(event: React.PointerEvent) {
    const drag = dragRef.current
    const page = pageRef.current
    if (!drag || !page) return
    const rect = page.getBoundingClientRect()
    const dx = ((event.clientX - drag.startX) / rect.width) * 100
    const dy = ((event.clientY - drag.startY) / rect.height) * 100
    if (drag.kind === 'panel') {
      updatePanel(drag.id, {
        position_x: clamp(drag.originalX + dx, 0, 100 - drag.originalWidth),
        position_y: clamp(drag.originalY + dy, 0, 100 - drag.originalHeight),
      })
    } else if (drag.kind === 'resize-panel') {
      updatePanel(drag.id, {
        width: clamp(drag.originalWidth + dx, 8, 100 - drag.originalX),
        height: clamp(drag.originalHeight + dy, 8, 100 - drag.originalY),
      })
    } else if (drag.kind === 'balloon') {
      updateBalloon(drag.id, {
        position_x: clamp(drag.originalX + dx, 0, 100 - drag.originalWidth),
        position_y: clamp(drag.originalY + dy, 0, 100 - drag.originalHeight),
      })
    } else {
      updateBalloon(drag.id, {
        width: clamp(drag.originalWidth + dx, 8, 100 - drag.originalX),
        height: clamp(drag.originalHeight + dy, 6, 100 - drag.originalY),
      })
    }
  }

  function endDrag() {
    dragRef.current = null
  }

  async function saveCanvas() {
    if (!comic || !selectedPage) return
    setBusy(true)
    setMessage('')
    try {
      const updated = await api<Comic>(`/teacher-studio/comics/${comic.id}/canvas`, {
        method: 'POST',
        body: JSON.stringify({
          expected_revision: comic.edit_revision,
          page_id: selectedPage.id,
          panels: selectedPage.panels.map((panel) => ({
            panel_id: panel.id,
            position_x: panel.position_x,
            position_y: panel.position_y,
            width: panel.width,
            height: panel.height,
            rotation: panel.rotation,
            z_index: panel.z_index,
          })),
          balloons: selectedPage.panels.flatMap((panel) => panel.balloons.map((balloon) => ({
            balloon_id: balloon.id,
            position_x: balloon.position_x,
            position_y: balloon.position_y,
            width: balloon.width,
            height: balloon.height,
            layer_config: balloon.layer_config,
          }))),
          canvas_config: { zoom, snap: true, guides: true },
        }),
      })
      setComic(updated)
      setDirty(false)
      setMessage('Página salva e versionada.')
    } catch (error) {
      setMessage((error as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function addPage() {
    if (!comic) return
    const updated = await api<Comic>(`/teacher-studio/comics/${comic.id}/pages`, {
      method: 'POST',
      body: JSON.stringify({ role: 'story', panel_count: 4, layout_template: 'grid_2x2' }),
    })
    setComic(updated)
    setSelectedPageId(updated.pages.at(-1)?.id ?? null)
  }

  async function duplicatePage() {
    if (!comic || !selectedPage) return
    const updated = await api<Comic>(`/teacher-studio/comics/${comic.id}/pages/${selectedPage.id}/duplicate`, { method: 'POST' })
    setComic(updated)
    setSelectedPageId(updated.pages.at(-1)?.id ?? null)
  }

  async function deletePage() {
    if (!comic || !selectedPage || comic.pages.length <= 1) return
    await api(`/teacher-studio/comics/${comic.id}/pages/${selectedPage.id}`, { method: 'DELETE' })
    await load()
    setSelectedPageId(comic.pages.find((page) => page.id !== selectedPage.id)?.id ?? null)
  }

  async function movePage(direction: -1 | 1) {
    if (!comic || !selectedPage) return
    const index = comic.pages.findIndex((page) => page.id === selectedPage.id)
    const next = index + direction
    if (next < 0 || next >= comic.pages.length) return
    const ids = comic.pages.map((page) => page.id)
    ;[ids[index], ids[next]] = [ids[next], ids[index]]
    const updated = await api<Comic>(`/teacher-studio/comics/${comic.id}/pages/reorder`, {
      method: 'POST', body: JSON.stringify({ page_ids: ids }),
    })
    setComic(updated)
  }

  if (!comic || !selectedPage) return <div className="loading-card">Carregando canvas…</div>

  return (
    <div className="canvas-app">
      <header className="canvas-toolbar">
        <div><Link to="/estudio-professor">← Estúdio</Link><strong>{comic.title}</strong><span>{dirty ? 'Alterações não salvas' : `v${comic.current_version}`}</span></div>
        <div className="toolbar-actions">
          <button onClick={() => setZoom((value) => clamp(value - 0.1, 0.4, 1.3))} type="button">−</button>
          <span>{Math.round(zoom * 100)}%</span>
          <button onClick={() => setZoom((value) => clamp(value + 0.1, 0.4, 1.3))} type="button">+</button>
          <button disabled={busy || !dirty} onClick={() => void saveCanvas()} type="button" className="primary">{busy ? 'Salvando…' : 'Salvar página'}</button>
        </div>
      </header>
      {message ? <div className="canvas-message">{message}</div> : null}

      <div className="canvas-layout">
        <aside className="page-rail">
          <div className="rail-title"><strong>Páginas</strong><button onClick={() => void addPage()} type="button">＋</button></div>
          {comic.pages.map((page) => (
            <button key={page.id} className={page.id === selectedPage.id ? 'page-thumb active' : 'page-thumb'} onClick={() => { setSelectedPageId(page.id); setSelection(null) }} type="button">
              <span>{page.page_number}</span><div>{page.panels.map((panel) => <i key={panel.id} style={{ left: `${panel.position_x}%`, top: `${panel.position_y}%`, width: `${panel.width}%`, height: `${panel.height}%` }} />)}</div><small>{page.page_role}</small>
            </button>
          ))}
          <div className="page-actions"><button onClick={() => void movePage(-1)} type="button">↑</button><button onClick={() => void movePage(1)} type="button">↓</button><button onClick={() => void duplicatePage()} type="button">Duplicar</button><button disabled={comic.pages.length <= 1} onClick={() => void deletePage()} type="button">Excluir</button></div>
        </aside>

        <main className="canvas-stage" onPointerMove={moveDrag} onPointerUp={endDrag} onPointerCancel={endDrag}>
          <div className="page-canvas-wrap" style={{ transform: `scale(${zoom})` }}>
            <div ref={pageRef} className={`page-canvas orientation-${selectedPage.orientation}`} onPointerDown={() => setSelection(null)}>
              <div className="safe-area" />
              {selectedPage.panels.map((panel) => (
                <div
                  key={panel.id}
                  className={`canvas-panel shape-${panel.shape} ${selection?.kind === 'panel' && selection.id === panel.id ? 'selected' : ''}`}
                  style={{ left: `${panel.position_x}%`, top: `${panel.position_y}%`, width: `${panel.width}%`, height: `${panel.height}%`, transform: `rotate(${panel.rotation}deg)`, zIndex: panel.z_index }}
                  onPointerDown={(event) => { setSelection({ kind: 'panel', id: panel.id }); beginDrag(event, { kind: 'panel', id: panel.id, startX: event.clientX, startY: event.clientY, originalX: panel.position_x, originalY: panel.position_y, originalWidth: panel.width, originalHeight: panel.height }) }}
                >
                  <div className="panel-image-placeholder"><span>Quadro {panel.reading_order}</span><small>{panel.scene_description || 'Imagem da cena'}</small></div>
                  {panel.balloons.map((balloon) => (
                    <div
                      key={balloon.id}
                      className={`canvas-balloon balloon-${balloon.balloon_type} ${selection?.kind === 'balloon' && selection.id === balloon.id ? 'selected' : ''}`}
                      style={{ left: `${balloon.position_x}%`, top: `${balloon.position_y}%`, width: `${balloon.width}%`, height: `${balloon.height}%` }}
                      onPointerDown={(event) => { setSelection({ kind: 'balloon', id: balloon.id }); beginDrag(event, { kind: 'balloon', id: balloon.id, startX: event.clientX, startY: event.clientY, originalX: balloon.position_x, originalY: balloon.position_y, originalWidth: balloon.width, originalHeight: balloon.height }) }}
                    >
                      <span>{balloon.text}</span>
                      {!balloon.is_locked ? <i onPointerDown={(event) => beginDrag(event, { kind: 'resize-balloon', id: balloon.id, startX: event.clientX, startY: event.clientY, originalX: balloon.position_x, originalY: balloon.position_y, originalWidth: balloon.width, originalHeight: balloon.height })} /> : null}
                    </div>
                  ))}
                  <b className="resize-handle" onPointerDown={(event) => beginDrag(event, { kind: 'resize-panel', id: panel.id, startX: event.clientX, startY: event.clientY, originalX: panel.position_x, originalY: panel.position_y, originalWidth: panel.width, originalHeight: panel.height })} />
                </div>
              ))}
            </div>
          </div>
        </main>

        <aside className="properties-panel">
          <h2>Propriedades</h2>
          {!selection ? <p>Selecione um quadro ou balão para editar.</p> : null}
          {selectedPanel ? <PanelProperties panel={selectedPanel} update={(patch) => updatePanel(selectedPanel.id, patch)} /> : null}
          {selectedBalloon ? <BalloonProperties balloon={selectedBalloon} update={(patch) => updateBalloon(selectedBalloon.id, patch)} /> : null}
          <h2>Camadas</h2>
          <div className="layers-list">
            {selectedPage.panels.slice().sort((a, b) => b.z_index - a.z_index).map((panel) => <button key={panel.id} onClick={() => setSelection({ kind: 'panel', id: panel.id })} type="button"><span>▣</span> Quadro {panel.reading_order}<small>{panel.balloons.length} balões</small></button>)}
          </div>
        </aside>
      </div>
    </div>
  )
}

function PanelProperties({ panel, update }: { panel: ComicPanel; update: (patch: Partial<ComicPanel>) => void }) {
  return <div className="property-form">
    <label>Formato<select value={panel.shape} onChange={(event) => update({ shape: event.target.value as ComicPanel['shape'] })}><option value="rectangle">Retangular</option><option value="horizontal">Horizontal</option><option value="vertical">Vertical</option><option value="square">Quadrado</option><option value="circle">Circular</option><option value="oval">Oval</option><option value="panoramic">Panorâmico</option></select></label>
    <label>Largura<input type="number" value={panel.width} onChange={(event) => update({ width: Number(event.target.value) })} /></label>
    <label>Altura<input type="number" value={panel.height} onChange={(event) => update({ height: Number(event.target.value) })} /></label>
    <label>Rotação<input min={-20} max={20} type="range" value={panel.rotation} onChange={(event) => update({ rotation: Number(event.target.value) })} /></label>
    <label>Descrição<textarea value={panel.scene_description} onChange={(event) => update({ scene_description: event.target.value })} /></label>
  </div>
}

function BalloonProperties({ balloon, update }: { balloon: ComicBalloon; update: (patch: Partial<ComicBalloon>) => void }) {
  return <div className="property-form">
    <label>Tipo<select value={balloon.balloon_type} onChange={(event) => update({ balloon_type: event.target.value as ComicBalloon['balloon_type'] })}><option value="speech">Fala</option><option value="thought">Pensamento</option><option value="shout">Grito</option><option value="whisper">Sussurro</option><option value="narration">Narração</option><option value="caption">Legenda</option><option value="pedagogical">Explicação</option></select></label>
    <label>Texto<textarea value={balloon.text} onChange={(event) => update({ text: event.target.value })} /></label>
    <label>Largura<input type="number" value={balloon.width} onChange={(event) => update({ width: Number(event.target.value) })} /></label>
    <label>Altura<input type="number" value={balloon.height} onChange={(event) => update({ height: Number(event.target.value) })} /></label>
  </div>
}
