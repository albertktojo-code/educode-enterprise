import { useEffect, useMemo, useState } from 'react'

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

export function AnimeStudentLibraryPage() {
  const [items, setItems] = useState<AnimePublicationLibraryItem[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [videoUrl, setVideoUrl] = useState('')
  const [captionUrl, setCaptionUrl] = useState('')
  const [transcript, setTranscript] = useState<AnimePublicationTranscriptCue[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [mediaLoading, setMediaLoading] = useState(false)
  const [error, setError] = useState('')

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
    setMediaLoading(true)
    setError('')
    void Promise.all([
      animeStudioApi.publicationMedia(selectedId),
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
  }, [selectedId])

  const selected = items.find((item) => item.publication.project_id === selectedId) ?? null
  const filtered = useMemo(() => {
    const query = search.trim().toLocaleLowerCase('pt-BR')
    if (!query) return items
    return items.filter((item) =>
      `${item.publication.title} ${item.synopsis}`.toLocaleLowerCase('pt-BR').includes(query),
    )
  }, [items, search])

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
          <div>{filtered.map((item) => <button type="button" className={selectedId === item.publication.project_id ? 'is-active' : ''} key={item.publication.project_id} onClick={() => setSelectedId(item.publication.project_id)}><span aria-hidden="true">▶</span><div><b>{item.publication.title}</b><small>{formatDuration(item.duration_ms)} · {item.publication.width}×{item.publication.height}</small></div></button>)}</div>
        </aside>

        <main>
          {selected ? <>
            <div className="anime-student-player">{mediaLoading || !videoUrl ? <div role="status">Preparando vídeo…</div> : <video key={selectedId} controls playsInline preload="metadata"><source src={videoUrl} type={`video/${selected.publication.format}`} />{captionUrl ? <track default kind="captions" src={captionUrl} srcLang={selected.publication.caption_languages[0] ?? 'pt-BR'} label="Português" /> : null}</video>}</div>
            <section className="anime-student-copy"><div><span>PUBLICADO PELO PROFESSOR</span><h2>{selected.publication.title}</h2><p>{selected.synopsis || 'Produção audiovisual educacional da sua turma.'}</p></div><ul><li>{selected.publication.caption_languages.length ? 'CC Legendas' : 'Sem legendas'}</li><li>{selected.publication.includes_transcript ? 'Transcrição' : 'Sem transcrição'}</li><li>{selected.publication.includes_audio_description ? 'Audiodescrição' : 'Áudio original'}</li></ul></section>
            {selected.publication.includes_transcript ? <section className="anime-transcript"><header><span>ACESSIBILIDADE</span><h2>Transcrição</h2></header>{transcript.length ? <ol>{transcript.map((cue, index) => <li key={`${cue.start_ms}-${index}`}><time>{formatDuration(cue.start_ms)}</time><p>{cue.speaker ? <strong>{cue.speaker}: </strong> : null}{cue.text}</p></li>)}</ol> : <p>A transcrição ainda não possui trechos.</p>}</section> : null}
          </> : null}
        </main>
      </div> : null}
    </section>
  )
}
