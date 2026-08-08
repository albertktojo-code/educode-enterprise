import { useEffect, useMemo, useRef, useState } from 'react'

import { EmptyState } from '../../components/EmptyState'
import { LoadingState } from '../../components/LoadingState'
import { animeStudioApi } from './api'
import type {
  AnimePublicationLibraryItem,
  AnimePublicationTranscriptCue,
} from './types'
import './studentStyles.css'

function formatDuration(milliseconds: number): string {
  const totalSeconds = Math.round(milliseconds / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  return `${minutes}:${String(totalSeconds % 60).padStart(2, '0')}`
}

function progressKey(projectId: string, revision: number): string {
  return `educode_anime_progress_${projectId}_${revision}`
}

function automaticRendition(item: AnimePublicationLibraryItem | null) {
  if (!item?.publication.renditions.length) return null
  const connection = (navigator as Navigator & {
    connection?: { effectiveType?: string; saveData?: boolean }
  }).connection
  const constrained = connection?.saveData
    || ['slow-2g', '2g', '3g'].includes(connection?.effectiveType ?? '')
  const targetWidth = constrained
    ? 640
    : Math.max(640, Math.round(window.innerWidth * Math.min(window.devicePixelRatio, 2)))
  const ordered = [...item.publication.renditions]
    .sort((left, right) => left.width - right.width)
  return [...ordered].reverse()
    .find((rendition) => rendition.width <= targetWidth) ?? ordered[0]
}

export function AnimeStudentLibraryPage() {
  const [items, setItems] = useState<AnimePublicationLibraryItem[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedRenditionId, setSelectedRenditionId] = useState('auto')
  const [videoUrl, setVideoUrl] = useState('')
  const [captionUrl, setCaptionUrl] = useState('')
  const [transcript, setTranscript] = useState<AnimePublicationTranscriptCue[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [mediaLoading, setMediaLoading] = useState(false)
  const [error, setError] = useState('')
  const [playbackRate, setPlaybackRate] = useState(1)
  const [positionSeconds, setPositionSeconds] = useState(0)
  const [durationSeconds, setDurationSeconds] = useState(0)
  const [resumeMessage, setResumeMessage] = useState('')
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const lastSavedSecond = useRef(-1)

  useEffect(() => {
    animeStudioApi.listPublications()
      .then((rows) => {
        setItems(rows)
        setSelectedId(rows[0]?.publication.project_id ?? null)
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedId) return undefined
    let active = true
    let nextVideoUrl = ''
    let nextCaptionUrl = ''
    const item = items.find((row) => row.publication.project_id === selectedId) ?? null
    const renditionId = selectedRenditionId === 'auto'
      ? automaticRendition(item)?.asset_file_id
      : selectedRenditionId
    setMediaLoading(true)
    setError('')
    setPositionSeconds(0)
    setDurationSeconds(0)
    lastSavedSecond.current = -1
    void Promise.all([
      animeStudioApi.publicationMedia(selectedId, renditionId),
      animeStudioApi.publicationCaptions(selectedId),
      animeStudioApi.publicationTranscript(selectedId),
    ]).then(([video, captions, cues]) => {
      if (!active) return
      nextVideoUrl = URL.createObjectURL(video)
      nextCaptionUrl = URL.createObjectURL(captions)
      setVideoUrl(nextVideoUrl)
      setCaptionUrl(nextCaptionUrl)
      setTranscript(cues)
    }).catch((reason: Error) => {
      if (active) setError(reason.message)
    }).finally(() => {
      if (active) setMediaLoading(false)
    })
    return () => {
      active = false
      if (nextVideoUrl) URL.revokeObjectURL(nextVideoUrl)
      if (nextCaptionUrl) URL.revokeObjectURL(nextCaptionUrl)
    }
  }, [items, selectedId, selectedRenditionId])

  const selected = items.find(
    (item) => item.publication.project_id === selectedId,
  ) ?? null
  const selectedRendition = selectedRenditionId === 'auto'
    ? automaticRendition(selected)
    : selected?.publication.renditions.find(
      (rendition) => rendition.asset_file_id === selectedRenditionId,
    ) ?? selected?.publication.renditions[0] ?? null
  const filtered = useMemo(() => {
    const query = search.trim().toLocaleLowerCase('pt-BR')
    if (!query) return items
    return items.filter((item) =>
      `${item.publication.title} ${item.synopsis}`
        .toLocaleLowerCase('pt-BR').includes(query),
    )
  }, [items, search])

  function restoreProgress(video: HTMLVideoElement) {
    if (!selected) return
    video.playbackRate = playbackRate
    setDurationSeconds(Number.isFinite(video.duration) ? video.duration : 0)
    try {
      const stored = JSON.parse(localStorage.getItem(progressKey(
        selected.publication.project_id,
        selected.publication.render_revision,
      )) ?? '{}') as { position?: number }
      const position = Number(stored.position ?? 0)
      if (position >= 5 && position < video.duration - 5) {
        video.currentTime = position
        setPositionSeconds(position)
        setResumeMessage(`Retomado em ${formatDuration(position * 1000)}.`)
      } else {
        setResumeMessage('')
      }
    } catch {
      setResumeMessage('')
    }
  }

  function saveProgress(video: HTMLVideoElement, force = false) {
    if (!selected || !Number.isFinite(video.currentTime)) return
    const second = Math.floor(video.currentTime)
    setPositionSeconds(video.currentTime)
    setDurationSeconds(Number.isFinite(video.duration) ? video.duration : 0)
    if (!force && second === lastSavedSecond.current) return
    lastSavedSecond.current = second
    localStorage.setItem(progressKey(
      selected.publication.project_id,
      selected.publication.render_revision,
    ), JSON.stringify({
      position: video.currentTime,
      duration: video.duration,
      updated_at: new Date().toISOString(),
    }))
  }

  function seekTo(milliseconds: number) {
    if (!videoRef.current) return
    videoRef.current.currentTime = milliseconds / 1000
    videoRef.current.focus()
    void videoRef.current.play()
  }

  return (
    <section className="anime-student-library">
      <header className="anime-library-hero">
        <div><span>EDUCODE PLAY</span><h1>Vídeos da minha turma</h1><p>Assista às produções compartilhadas pelos seus professores com legendas e transcrição.</p></div>
        <label><span className="sr-only">Buscar vídeo</span><input type="search" placeholder="Buscar por título ou assunto" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
      </header>

      {error ? <div className="alert error" role="alert">{error}</div> : null}
      {loading ? <LoadingState label="Carregando vídeos autorizados" rows={3} /> : null}
      {!loading && !items.length ? <EmptyState icon="folder" title="Nenhum vídeo disponível" description="Quando um professor publicar um vídeo para sua turma, ele aparecerá aqui." /> : null}

      {!loading && items.length ? <div className="anime-library-layout">
        <aside aria-label="Vídeos disponíveis">
          <strong>{filtered.length} {filtered.length === 1 ? 'vídeo' : 'vídeos'}</strong>
          <div>{filtered.map((item) => <button type="button" className={selectedId === item.publication.project_id ? 'is-active' : ''} key={item.publication.project_id} onClick={() => { setSelectedId(item.publication.project_id); setSelectedRenditionId('auto'); setResumeMessage('') }}><span aria-hidden="true">▶</span><div><b>{item.publication.title}</b><small>{formatDuration(item.duration_ms)} · {item.publication.width}×{item.publication.height}</small></div></button>)}</div>
        </aside>

        <main>
          {selected ? <>
            <div className="anime-student-player">{mediaLoading || !videoUrl ? <div role="status">Preparando vídeo…</div> : <video ref={videoRef} key={`${selectedId}-${selectedRendition?.asset_file_id ?? 'source'}`} controls playsInline preload="metadata" onLoadedMetadata={(event) => restoreProgress(event.currentTarget)} onTimeUpdate={(event) => saveProgress(event.currentTarget)} onPause={(event) => saveProgress(event.currentTarget, true)} onEnded={(event) => { saveProgress(event.currentTarget, true); setResumeMessage('Vídeo concluído.') }}><source src={videoUrl} type={`video/${selected.publication.format}`} />{captionUrl ? <track default kind="captions" src={captionUrl} srcLang={selected.publication.caption_languages[0] ?? 'pt-BR'} label="Português" /> : null}</video>}</div>
            <div className="anime-playback-progress" aria-live="polite"><div><span>{resumeMessage || 'Seu progresso é salvo neste dispositivo.'}</span><strong>{durationSeconds ? `${Math.round((positionSeconds / durationSeconds) * 100)}%` : '0%'}</strong></div><progress max={Math.max(durationSeconds, 1)} value={positionSeconds}>{positionSeconds}</progress></div>
            <section className="anime-student-copy"><div><span>PUBLICADO PELO PROFESSOR</span><h2>{selected.publication.title}</h2><p>{selected.synopsis || 'Produção audiovisual educacional da sua turma.'}</p></div><div className="anime-quality-tools"><label>Velocidade<select value={playbackRate} onChange={(event) => { const rate = Number(event.target.value); setPlaybackRate(rate); if (videoRef.current) videoRef.current.playbackRate = rate }}><option value={0.75}>0,75×</option><option value={1}>Normal</option><option value={1.25}>1,25×</option><option value={1.5}>1,5×</option><option value={2}>2×</option></select></label>{selected.publication.renditions.length > 1 ? <label>Qualidade<select value={selectedRenditionId} onChange={(event) => setSelectedRenditionId(event.target.value)}><option value="auto">Automática</option>{selected.publication.renditions.map((rendition) => <option value={rendition.asset_file_id} key={rendition.asset_file_id}>{rendition.label} · {rendition.width}×{rendition.height}</option>)}</select></label> : null}<ul><li>{selected.publication.caption_languages.length ? 'CC Legendas' : 'Sem legendas'}</li><li>{selected.publication.includes_transcript ? 'Transcrição navegável' : 'Sem transcrição'}</li><li>{selected.publication.includes_audio_description ? 'Audiodescrição disponível' : 'Áudio original'}</li></ul></div></section>
            {selected.publication.includes_transcript ? <section className="anime-transcript"><header><span>ACESSIBILIDADE</span><h2>Transcrição</h2><p>Selecione um trecho para avançar o vídeo.</p></header>{transcript.length ? <ol>{transcript.map((cue, index) => <li className={cue.cue_kind === 'audio_description' ? 'is-audio-description' : ''} key={`${cue.start_ms}-${index}`}><button type="button" onClick={() => seekTo(cue.start_ms)}><time>{formatDuration(cue.start_ms)}</time><p>{cue.speaker ? <strong>{cue.speaker}: </strong> : null}{cue.text}</p></button></li>)}</ol> : <p>A transcrição ainda não possui trechos.</p>}</section> : null}
          </> : null}
        </main>
      </div> : null}
    </section>
  )
}
