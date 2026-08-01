import type { MouseEvent } from 'react'

import type { ComicPage, ComicPanel } from '../types/comic'

interface Props {
  page: ComicPage
  selectedPanelId?: string
  showTeacherOverlay?: boolean
  onSelectPanel?: (panel: ComicPanel, point: { x: number; y: number }) => void
  compact?: boolean
}

function panelRadius(shape: ComicPanel['shape']) {
  if (shape === 'circle' || shape === 'oval') return '50%'
  if (shape === 'square') return '4px'
  return '8px'
}

export function ComicPreviewSurface({
  page,
  selectedPanelId,
  showTeacherOverlay = false,
  onSelectPanel,
  compact = false,
}: Props) {
  const ratio = page.orientation === 'landscape' ? '297 / 210' : '210 / 297'
  return (
    <div
      className={`preview-page-surface ${compact ? 'compact' : ''}`}
      style={{ aspectRatio: ratio }}
      aria-label={`Página ${page.page_number}`}
    >
      <div className="preview-page-label">
        <strong>{page.title || `Página ${page.page_number}`}</strong>
        <span>{page.page_role}</span>
      </div>
      {page.panels.map((panel) => (
        <button
          className={`preview-panel-surface ${selectedPanelId === panel.id ? 'selected' : ''}`}
          key={panel.id}
          onClick={(event: MouseEvent<HTMLButtonElement>) => {
            const bounds = event.currentTarget.getBoundingClientRect()
            const x = ((event.clientX - bounds.left) / bounds.width) * 100
            const y = ((event.clientY - bounds.top) / bounds.height) * 100
            onSelectPanel?.(panel, {
              x: Math.max(0, Math.min(100, Number(x.toFixed(2)))),
              y: Math.max(0, Math.min(100, Number(y.toFixed(2)))),
            })
          }}
          type="button"
          style={{
            left: `${panel.position_x}%`,
            top: `${panel.position_y}%`,
            width: `${panel.width}%`,
            height: `${panel.height}%`,
            borderRadius: panelRadius(panel.shape),
            transform: `rotate(${panel.rotation}deg)`,
            zIndex: panel.z_index + 1,
          }}
        >
          {panel.image_asset_path ? (
            <img alt={panel.alt_text || ''} src={panel.image_asset_path} />
          ) : (
            <div className="preview-scene-placeholder">
              <span>Quadro {panel.panel_number}</span>
              <p>{panel.scene_description || panel.narrative_goal || 'Cena aguardando imagem'}</p>
            </div>
          )}
          {panel.balloons.map((balloon) => (
            <div
              className={`preview-balloon balloon-${balloon.balloon_type}`}
              key={balloon.id}
              style={{
                left: `${balloon.position_x}%`,
                top: `${balloon.position_y}%`,
                width: `${balloon.width}%`,
                minHeight: `${balloon.height}%`,
              }}
            >
              {balloon.speaker_name_snapshot ? <strong>{balloon.speaker_name_snapshot}</strong> : null}
              <span>{balloon.text}</span>
            </div>
          ))}
          {showTeacherOverlay ? (
            <div className={`preview-review-badge status-${panel.preview_review_status}`}>
              {panel.preview_review_status.replaceAll('_', ' ')}
            </div>
          ) : null}
        </button>
      ))}
    </div>
  )
}
