import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import type { AssignmentSummary } from '../../types/delivery'
import type { AnimeInteractiveCheckpoint, AnimeProject } from './types'
import { readProjectCheckpoints } from './checkpointUtils'

function formatTime(milliseconds: number): string {
  const totalSeconds = Math.round(milliseconds / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  return `${minutes}:${String(totalSeconds % 60).padStart(2, '0')}`
}

interface AnimeCheckpointEditorProps {
  project: AnimeProject
  assignments: AssignmentSummary[]
  durationMs: number
  busy: boolean
  onChange: (
    checkpoints: AnimeInteractiveCheckpoint[],
    successMessage: string,
  ) => Promise<void>
}

export function AnimeCheckpointEditor({
  project,
  assignments,
  durationMs,
  busy,
  onChange,
}: AnimeCheckpointEditorProps) {
  const [previewMs, setPreviewMs] = useState(0)
  const checkpoints = useMemo(() => readProjectCheckpoints(project), [project])
  const availableAssignments = useMemo(
    () => assignments.filter((assignment) => (
      assignment.status === 'scheduled' || assignment.status === 'published'
    )),
    [assignments],
  )
  const activePreview = [...checkpoints]
    .reverse()
    .find((checkpoint) => checkpoint.timestamp_ms <= previewMs) ?? null

  async function addCheckpoint(data: FormData) {
    const timestampMs = Math.round(Number(data.get('timestamp_seconds') ?? 0) * 1000)
    const label = String(data.get('label') ?? '').trim()
    const assignmentId = String(data.get('assignment_id') ?? '')
    if (!label || !assignmentId || timestampMs < 0 || timestampMs > durationMs) return
    const next = [
      ...checkpoints,
      {
        id: crypto.randomUUID(),
        timestamp_ms: timestampMs,
        label,
        assignment_id: assignmentId,
        pause_playback: data.get('pause_playback') === 'on',
        required: data.get('required') === 'on',
      },
    ].sort((left, right) => left.timestamp_ms - right.timestamp_ms)
    await onChange(next, 'Checkpoint adicionado à experiência audiovisual.')
    setPreviewMs(timestampMs)
  }

  async function updateCheckpoint(checkpoint: AnimeInteractiveCheckpoint, data: FormData) {
    const timestampMs = Math.round(Number(data.get('timestamp_seconds') ?? 0) * 1000)
    const label = String(data.get('label') ?? '').trim()
    const assignmentId = String(data.get('assignment_id') ?? '')
    if (!label || !assignmentId || timestampMs < 0 || timestampMs > durationMs) return
    const next = checkpoints
      .map((item) => item.id === checkpoint.id ? {
        ...item,
        timestamp_ms: timestampMs,
        label,
        assignment_id: assignmentId,
        pause_playback: data.get('pause_playback') === 'on',
        required: data.get('required') === 'on',
      } : item)
      .sort((left, right) => left.timestamp_ms - right.timestamp_ms)
    await onChange(next, 'Checkpoint atualizado.')
    setPreviewMs(timestampMs)
  }

  async function removeCheckpoint(checkpointId: string) {
    await onChange(
      checkpoints.filter((checkpoint) => checkpoint.id !== checkpointId),
      'Checkpoint removido.',
    )
  }

  return (
    <section className="anime-checkpoint-workspace">
      <div className="anime-checkpoint-board">
        <header>
          <div>
            <span className="anime-eyebrow">Studio + Assess</span>
            <h2>Experiência interativa</h2>
            <p>Posicione atividades canônicas ao longo do vídeo antes de publicar.</p>
          </div>
          <strong>{checkpoints.length} checkpoint(s)</strong>
        </header>

        <div className="anime-checkpoint-preview" aria-live="polite">
          <span>{formatTime(previewMs)} de {formatTime(durationMs)}</span>
          {activePreview ? (
            <article>
              <small>PRÉVIA DA INTERAÇÃO</small>
              <strong>{activePreview.label}</strong>
              <p>{activePreview.pause_playback ? 'O vídeo será pausado.' : 'O aviso será exibido sem pausa.'}</p>
            </article>
          ) : (
            <p>Nenhuma atividade foi acionada até este instante.</p>
          )}
        </div>

        <div className="anime-checkpoint-timeline">
          <div aria-hidden="true">
            {checkpoints.map((checkpoint) => (
              <i
                key={checkpoint.id}
                style={{ left: `${durationMs ? (checkpoint.timestamp_ms / durationMs) * 100 : 0}%` }}
              />
            ))}
          </div>
          <label>
            Navegar pela prévia
            <input
              type="range"
              min="0"
              max={Math.max(durationMs, 1000)}
              step="100"
              value={previewMs}
              onChange={(event) => setPreviewMs(Number(event.target.value))}
            />
          </label>
          <ol>
            {checkpoints.map((checkpoint) => (
              <li key={checkpoint.id}>
                <button type="button" onClick={() => setPreviewMs(checkpoint.timestamp_ms)}>
                  <time>{formatTime(checkpoint.timestamp_ms)}</time>
                  <span>{checkpoint.label}</span>
                </button>
              </li>
            ))}
          </ol>
        </div>

        {checkpoints.length ? (
          <div className="anime-checkpoint-list">
            {checkpoints.map((checkpoint) => (
              <form
                key={checkpoint.id}
                onSubmit={(event) => {
                  event.preventDefault()
                  void updateCheckpoint(checkpoint, new FormData(event.currentTarget))
                }}
              >
                <label>Instante (s)<input name="timestamp_seconds" type="number" min="0" max={durationMs / 1000} step="0.1" defaultValue={checkpoint.timestamp_ms / 1000} required /></label>
                <label className="anime-checkpoint-label">Rótulo<input name="label" defaultValue={checkpoint.label} maxLength={180} required /></label>
                <label>Atividade<select name="assignment_id" defaultValue={checkpoint.assignment_id} required>{availableAssignments.map((assignment) => <option value={assignment.id} key={assignment.id}>{assignment.title}</option>)}</select></label>
                <label className="anime-check-row"><input name="pause_playback" type="checkbox" defaultChecked={checkpoint.pause_playback} /> Pausar vídeo</label>
                <label className="anime-check-row"><input name="required" type="checkbox" defaultChecked={checkpoint.required} /> Etapa obrigatória</label>
                <div><button type="submit" className="anime-button ghost" disabled={busy}>Salvar</button><button type="button" className="anime-icon-button danger" aria-label={`Excluir ${checkpoint.label}`} disabled={busy} onClick={() => void removeCheckpoint(checkpoint.id)}>×</button></div>
              </form>
            ))}
          </div>
        ) : (
          <div className="anime-empty-state compact"><span aria-hidden="true">◇</span><h3>Vídeo ainda sem atividades</h3><p>Use o formulário para criar o primeiro ponto de interação.</p></div>
        )}
      </div>

      <form
        className="anime-inspector"
        onSubmit={(event) => {
          event.preventDefault()
          void addCheckpoint(new FormData(event.currentTarget))
          event.currentTarget.reset()
        }}
      >
        <header><span className="anime-eyebrow">Novo checkpoint</span><h2>Vincular atividade</h2></header>
        {availableAssignments.length ? (
          <>
            <label>Instante (s)<input name="timestamp_seconds" type="number" min="0" max={durationMs / 1000} step="0.1" defaultValue={previewMs / 1000} required /></label>
            <label>Rótulo<input name="label" maxLength={180} placeholder="Hora de praticar" required /></label>
            <label>Atividade<select name="assignment_id" required>{availableAssignments.map((assignment) => <option value={assignment.id} key={assignment.id}>{assignment.title} · {assignment.status === 'published' ? 'publicada' : 'agendada'}</option>)}</select></label>
            <label className="anime-check-row"><input name="pause_playback" type="checkbox" defaultChecked /> Pausar o vídeo neste instante</label>
            <label className="anime-check-row"><input name="required" type="checkbox" /> Marcar como etapa obrigatória</label>
            <small>A atividade continuará usando tentativas, respostas, correção e notas do EduCode Assess.</small>
            <button type="submit" className="anime-button primary" disabled={busy || durationMs <= 0}>Adicionar checkpoint</button>
          </>
        ) : (
          <div className="anime-checkpoint-assignment-empty">
            <p>Publique ou agende uma atividade antes de vinculá-la ao vídeo.</p>
            <Link to="/publicacoes">Abrir EduCode Assess</Link>
          </div>
        )}
      </form>
    </section>
  )
}
