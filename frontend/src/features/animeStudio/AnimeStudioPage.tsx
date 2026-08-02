import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'

import { animeStudioApi } from './api'
import {
  overlappingCaptionIds,
  parseCaptionFile,
  serializeCaptions,
} from './captionFiles'
import type {
  AnimeAudioTrack,
  AnimeCaptionCue,
  AnimeMediaGeneration,
  AnimeMediaGenerationKind,
  AnimeProject,
  AnimeProjectSummary,
  AnimeRender,
  AnimeRenderJob,
  AnimeScene,
} from './types'
import './styles.css'

type StudioTab = 'storyboard' | 'generation' | 'audio' | 'captions' | 'render'

const statusLabels: Record<string, string> = {
  draft: 'Rascunho',
  rendering: 'Renderizando',
  in_review: 'Em revisão',
  ready: 'Pronto',
  approved: 'Aprovado',
  rejected: 'Ajustes solicitados',
  queued: 'Na fila',
  processing: 'Processando',
  failed: 'Falhou',
}

const trackLabels: Record<string, string> = {
  dialogue: 'Diálogo',
  narration: 'Narração',
  music: 'Música',
  sfx: 'Efeito',
  audio_description: 'Audiodescrição',
}

const generationLabels: Record<AnimeMediaGenerationKind, string> = {
  image: 'Imagem',
  animation: 'Animação',
  voice: 'Voz',
  lip_sync: 'Sincronização labial',
  music: 'Trilha sonora',
  sfx: 'Efeito sonoro',
}

function formatDuration(milliseconds: number | null): string {
  if (!milliseconds) return '0:00'
  const totalSeconds = Math.round(milliseconds / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  return `${minutes}:${String(totalSeconds % 60).padStart(2, '0')}`
}

function SecureMedia({
  fileId,
  title,
  controls = false,
}: {
  fileId: string | null
  title: string
  controls?: boolean
}) {
  const [source, setSource] = useState<string | null>(null)
  const [mimeType, setMimeType] = useState('')

  useEffect(() => {
    let active = true
    let objectUrl = ''
    if (!fileId) {
      setSource(null)
      return undefined
    }
    void animeStudioApi
      .mediaBlob(fileId)
      .then((blob) => {
        if (!active) return
        objectUrl = URL.createObjectURL(blob)
        setMimeType(blob.type)
        setSource(objectUrl)
      })
      .catch(() => {
        if (active) setSource(null)
      })
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [fileId])

  if (!source) {
    return (
      <div className="anime-media-placeholder" aria-label={`${title} sem mídia`}>
        <span aria-hidden="true">◇</span>
        <small>Adicione imagem ou vídeo</small>
      </div>
    )
  }
  if (mimeType.startsWith('audio/')) {
    return <audio className="anime-audio-player" src={source} controls aria-label={title} />
  }
  if (mimeType.startsWith('video/')) {
    return (
      <video
        className="anime-media"
        src={source}
        controls={controls}
        muted={!controls}
        loop={!controls}
        playsInline
        aria-label={title}
      />
    )
  }
  return <img className="anime-media" src={source} alt={title} />
}

function ProjectRail({
  projects,
  selectedId,
  onSelect,
  onCreate,
}: {
  projects: AnimeProjectSummary[]
  selectedId: string | null
  onSelect: (id: string) => void
  onCreate: () => void
}) {
  return (
    <aside className="anime-project-rail" aria-label="Produções de anime">
      <header>
        <div>
          <span className="anime-eyebrow">Produções</span>
          <h2>Meus animes</h2>
        </div>
        <button className="anime-icon-button" onClick={onCreate} type="button" aria-label="Nova produção">
          +
        </button>
      </header>
      {projects.length ? (
        <div className="anime-project-list">
          {projects.map((project) => (
            <button
              type="button"
              key={project.id}
              className={project.id === selectedId ? 'is-active' : ''}
              onClick={() => onSelect(project.id)}
            >
              <span className="anime-project-thumbnail" aria-hidden="true">
                ▶
              </span>
              <span>
                <strong>{project.title}</strong>
                <small>
                  {statusLabels[project.status] ?? project.status} · v{project.revision}
                </small>
              </span>
            </button>
          ))}
        </div>
      ) : (
        <div className="anime-rail-empty">
          <span aria-hidden="true">✦</span>
          <p>Seu primeiro anime começa com uma ideia.</p>
          <button type="button" onClick={onCreate}>Criar produção</button>
        </div>
      )}
    </aside>
  )
}

function CreateProjectDialog({
  open,
  onClose,
  onSubmit,
  busy,
}: {
  open: boolean
  onClose: () => void
  onSubmit: (data: FormData) => Promise<void>
  busy: boolean
}) {
  if (!open) return null
  return (
    <div className="anime-dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="anime-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="new-anime-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header>
          <div>
            <span className="anime-eyebrow">Nova produção</span>
            <h2 id="new-anime-title">Dê vida à aprendizagem</h2>
          </div>
          <button type="button" className="anime-icon-button" onClick={onClose} aria-label="Fechar">×</button>
        </header>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            void onSubmit(new FormData(event.currentTarget))
          }}
        >
          <label>
            Título
            <input name="title" required minLength={3} placeholder="A jornada dos algoritmos" autoFocus />
          </label>
          <label>
            Sinopse pedagógica
            <textarea name="synopsis" rows={4} placeholder="Conte o que os estudantes vão descobrir..." />
          </label>
          <div className="anime-form-grid">
            <label>
              Estilo
              <select name="style">
                <option value="anime_school">Anime escolar</option>
                <option value="anime_adventure">Anime de aventura</option>
              </select>
            </label>
            <label>
              Formato
              <select name="ratio">
                <option value="16:9">Paisagem 16:9</option>
                <option value="9:16">Vertical 9:16</option>
                <option value="1:1">Quadrado 1:1</option>
                <option value="4:3">Clássico 4:3</option>
              </select>
            </label>
          </div>
          <label className="anime-check-row">
            <input type="checkbox" name="captions" defaultChecked />
            Preparar legendas e audiodescrição
          </label>
          <footer>
            <button type="button" className="anime-button ghost" onClick={onClose}>Cancelar</button>
            <button type="submit" className="anime-button primary" disabled={busy}>
              {busy ? 'Criando…' : 'Abrir estúdio'}
            </button>
          </footer>
        </form>
      </section>
    </div>
  )
}

export function AnimeStudioPage() {
  const [projects, setProjects] = useState<AnimeProjectSummary[]>([])
  const [project, setProject] = useState<AnimeProject | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedSceneId, setSelectedSceneId] = useState<string | null>(null)
  const [draggedSceneId, setDraggedSceneId] = useState<string | null>(null)
  const [mediaGenerations, setMediaGenerations] = useState<AnimeMediaGeneration[]>([])
  const [tab, setTab] = useState<StudioTab>('storyboard')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [captionPreviewMs, setCaptionPreviewMs] = useState(0)
  const [renderJobs, setRenderJobs] = useState<Record<string, AnimeRenderJob>>({})
  const [selectedRenderId, setSelectedRenderId] = useState<string | null>(null)
  const [comparisonRenderId, setComparisonRenderId] = useState<string | null>(null)

  const loadProjects = useCallback(async () => {
    const rows = await animeStudioApi.listProjects()
    setProjects(rows)
    setSelectedId((current) => current ?? rows[0]?.id ?? null)
  }, [])

  const loadProject = useCallback(async (projectId: string) => {
    const detail = await animeStudioApi.getProject(projectId)
    setProject(detail)
    setSelectedSceneId((current) =>
      detail.scenes.some((scene) => scene.id === current)
        ? current
        : detail.scenes[0]?.id ?? null,
    )
  }, [])

  const loadMediaGenerations = useCallback(async (projectId: string) => {
    setMediaGenerations(await animeStudioApi.listMediaGenerations(projectId))
  }, [])

  useEffect(() => {
    setLoading(true)
    void loadProjects()
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Falha ao carregar produções'))
      .finally(() => setLoading(false))
  }, [loadProjects])

  useEffect(() => {
    if (!selectedId) {
      setProject(null)
      return
    }
    setLoading(true)
    void Promise.all([loadProject(selectedId), loadMediaGenerations(selectedId)])
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Falha ao abrir produção'))
      .finally(() => setLoading(false))
  }, [loadMediaGenerations, loadProject, selectedId])

  useEffect(() => {
    if (!project || !mediaGenerations.some((job) => ['pending', 'queued', 'processing'].includes(job.status))) return undefined
    const timer = window.setInterval(() => {
      void loadMediaGenerations(project.id).catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : 'Falha ao atualizar gerações'),
      )
    }, 3000)
    return () => window.clearInterval(timer)
  }, [loadMediaGenerations, mediaGenerations, project])

  useEffect(() => {
    if (!project || !['rendering'].includes(project.status)) return undefined
    const timer = window.setInterval(() => {
      void loadProject(project.id).catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : 'Falha ao atualizar a renderização'),
      )
    }, 3000)
    return () => window.clearInterval(timer)
  }, [loadProject, project])

  useEffect(() => {
    const jobIds = (project?.renders ?? [])
      .map((render) => render.background_job_id)
      .filter((jobId): jobId is string => Boolean(jobId))
    if (!jobIds.length) {
      setRenderJobs({})
      return undefined
    }
    let active = true
    const refresh = async () => {
      const rows = await Promise.all(jobIds.map((jobId) => animeStudioApi.getRenderJob(jobId)))
      if (active) setRenderJobs(Object.fromEntries(rows.map((job) => [job.id, job])))
    }
    void refresh().catch(() => undefined)
    const timer = window.setInterval(() => {
      void refresh().catch(() => undefined)
    }, 3000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [project?.renders])

  const selectedScene = useMemo(
    () => project?.scenes.find((scene) => scene.id === selectedSceneId) ?? null,
    [project, selectedSceneId],
  )
  const latestRender = useMemo(
    () =>
      [...(project?.renders ?? [])].sort((a, b) => b.revision - a.revision)[0] ?? null,
    [project?.renders],
  )
  const activeRender = useMemo(() => {
    const activeId = String(project?.production_notes.active_render_id ?? '')
    return project?.renders.find((render) => render.id === activeId) ?? latestRender
  }, [latestRender, project?.production_notes.active_render_id, project?.renders])
  const selectedRender = useMemo(
    () => project?.renders.find((render) => render.id === selectedRenderId) ?? activeRender,
    [activeRender, project?.renders, selectedRenderId],
  )
  const comparisonRender = useMemo(
    () => project?.renders.find((render) => render.id === comparisonRenderId) ?? null,
    [comparisonRenderId, project?.renders],
  )
  const selectedRenderJob = selectedRender?.background_job_id
    ? renderJobs[selectedRender.background_job_id]
    : undefined
  const totalDuration = useMemo(
    () => project?.scenes.reduce((total, scene) => total + scene.duration_ms, 0) ?? 0,
    [project?.scenes],
  )
  const captionConflicts = useMemo(
    () => overlappingCaptionIds(project?.captions ?? []),
    [project?.captions],
  )
  const activeCaption = useMemo(
    () => project?.captions
      .filter((cue) => cue.start_ms <= captionPreviewMs && cue.end_ms > captionPreviewMs)
      .sort((a, b) => a.cue_order - b.cue_order)[0] ?? null,
    [captionPreviewMs, project?.captions],
  )

  async function execute(action: () => Promise<void>, successMessage: string) {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await action()
      setNotice(successMessage)
      await loadProjects()
      if (selectedId) await loadProject(selectedId)
      if (selectedId) await loadMediaGenerations(selectedId)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível concluir a ação')
    } finally {
      setBusy(false)
    }
  }

  async function createProject(data: FormData) {
    const ratio = String(data.get('ratio') ?? '16:9') as '16:9' | '9:16' | '1:1' | '4:3'
    const dimensions: Record<string, [number, number]> = {
      '16:9': [1920, 1080],
      '9:16': [1080, 1920],
      '1:1': [1080, 1080],
      '4:3': [1440, 1080],
    }
    await execute(async () => {
      const created = await animeStudioApi.createProject({
        title: String(data.get('title') ?? ''),
        synopsis: String(data.get('synopsis') ?? ''),
        style_preset_code: String(data.get('style') ?? 'anime_school'),
        aspect_ratio: ratio,
        width: dimensions[ratio][0],
        height: dimensions[ratio][1],
        fps: 24,
        language: 'pt-BR',
        accessibility_options: {
          captions: data.get('captions') === 'on',
          audio_description: data.get('captions') === 'on',
        },
      })
      setSelectedId(created.id)
      setProject(created)
      setDialogOpen(false)
    }, 'Produção criada. Agora monte a primeira cena.')
  }

  async function createScene(data: FormData) {
    if (!project) return
    const file = data.get('media')
    if (!(file instanceof File) || file.size === 0) {
      setError('Selecione uma imagem ou um vídeo para a cena.')
      return
    }
    await execute(async () => {
      const mediaKind = file.type.startsWith('video/') ? 'video' : 'image'
      const uploaded = await animeStudioApi.uploadMedia(
        project.id,
        file,
        mediaKind,
        `${project.title} · cena ${project.scenes.length + 1}`,
      )
      const scene = await animeStudioApi.createScene(project.id, {
        position: project.scenes.length + 1,
        title: String(data.get('title') ?? ''),
        duration_ms: Number(data.get('duration') ?? 5) * 1000,
        visual_asset_file_id: uploaded.file_id,
        screenplay_text: String(data.get('screenplay') ?? ''),
        visual_prompt: String(data.get('prompt') ?? ''),
        camera_settings: {
          shot_type: String(data.get('shot') ?? 'medium'),
          movement: String(data.get('camera') ?? 'static'),
        },
        transition_settings: { type: String(data.get('transition') ?? 'cut') },
      })
      setSelectedSceneId(scene.id)
    }, 'Cena adicionada à timeline.')
  }

  async function importStoryboard(data: FormData) {
    if (!project) return
    const comicId = String(data.get('comic_id') ?? '').trim()
    await execute(async () => {
      const result = await animeStudioApi.importStoryboard(project.id, comicId)
      setSelectedSceneId(result.scenes[0]?.id ?? selectedSceneId)
    }, 'Storyboard sincronizado com a HQ.')
  }

  async function saveSceneProperties(data: FormData) {
    if (!project || !selectedScene) return
    await execute(
      () => animeStudioApi.updateScene(project.id, selectedScene.id, {
        title: String(data.get('title') ?? selectedScene.title),
        duration_ms: Number(data.get('duration') ?? 5) * 1000,
        camera_settings: {
          ...selectedScene.camera_settings,
          shot_type: String(data.get('shot') ?? 'medium'),
          movement: String(data.get('camera') ?? 'static'),
        },
        transition_settings: {
          ...selectedScene.transition_settings,
          type: String(data.get('transition') ?? 'cut'),
        },
      }).then(() => undefined),
      'Cena atualizada na timeline.',
    )
  }

  async function moveScene(sceneId: string, offset: number) {
    if (!project) return
    const ids = project.scenes.map((scene) => scene.id)
    const from = ids.indexOf(sceneId)
    const to = Math.max(0, Math.min(ids.length - 1, from + offset))
    if (from === to) return
    ids.splice(to, 0, ids.splice(from, 1)[0])
    await execute(
      () => animeStudioApi.reorderTimeline(project.id, ids).then(() => undefined),
      'Timeline reorganizada.',
    )
  }

  async function dropScene(targetId: string) {
    if (!project || !draggedSceneId || draggedSceneId === targetId) return
    const ids = project.scenes.map((scene) => scene.id)
    const from = ids.indexOf(draggedSceneId)
    const to = ids.indexOf(targetId)
    ids.splice(to, 0, ids.splice(from, 1)[0])
    setDraggedSceneId(null)
    await execute(
      () => animeStudioApi.reorderTimeline(project.id, ids).then(() => undefined),
      'Timeline reorganizada.',
    )
  }

  async function splitSelectedScene(data: FormData) {
    if (!project || !selectedScene) return
    await execute(async () => {
      const result = await animeStudioApi.splitScene(
        project.id,
        selectedScene.id,
        Number(data.get('split_at') ?? 1) * 1000,
      )
      setSelectedSceneId(result.second.id)
    }, 'Cena dividida e preservada em duas partes.')
  }

  async function requestMediaGeneration(data: FormData) {
    if (!project) return
    const sceneId = String(data.get('scene_id') ?? '') || null
    const scene = project.scenes.find((item) => item.id === sceneId)
    await execute(async () => {
      await animeStudioApi.requestMediaGeneration(project.id, {
        scene_id: sceneId,
        kind: String(data.get('kind') ?? 'image') as AnimeMediaGenerationKind,
        prompt: String(data.get('prompt') ?? ''),
        duration_ms: Number(data.get('duration') ?? (scene?.duration_ms ?? 5000) / 1000) * 1000,
        voice_name: String(data.get('voice_name') ?? ''),
      })
      setTab('generation')
    }, 'Geração enviada para a fila com revisão humana obrigatória.')
  }

  async function reviewMediaGeneration(
    job: AnimeMediaGeneration,
    decision: 'approved' | 'rejected',
  ) {
    if (!project) return
    await execute(
      () => animeStudioApi.reviewMediaGeneration(project.id, job.id, decision).then(() => undefined),
      decision === 'approved' ? 'Mídia aprovada.' : 'Mídia rejeitada para nova geração.',
    )
  }

  async function createAudio(data: FormData) {
    if (!project) return
    const file = data.get('audio')
    if (!(file instanceof File) || file.size === 0) {
      setError('Selecione um arquivo de áudio.')
      return
    }
    await execute(async () => {
      const label = String(data.get('label') ?? 'Nova faixa')
      const uploaded = await animeStudioApi.uploadMedia(project.id, file, 'audio', label)
      await animeStudioApi.createAudioTrack(project.id, {
        scene_id: data.get('scene_id') || null,
        track_kind: String(data.get('kind') ?? 'dialogue'),
        label,
        language: 'pt-BR',
        asset_file_id: uploaded.file_id,
        transcript: String(data.get('transcript') ?? ''),
        speaker: String(data.get('speaker') ?? ''),
        start_ms: Number(data.get('start') ?? 0) * 1000,
        volume: Number(data.get('volume') ?? 1),
      })
    }, 'Faixa sincronizada com a produção.')
  }

  async function updateAudio(track: AnimeAudioTrack, data: FormData) {
    if (!project) return
    await execute(async () => {
      let assetFileId = track.asset_file_id
      const replacement = data.get('replacement')
      if (replacement instanceof File && replacement.size > 0) {
        const uploaded = await animeStudioApi.uploadMedia(
          project.id,
          replacement,
          'audio',
          `${track.label} · substituição`,
        )
        assetFileId = uploaded.file_id
      }
      await animeStudioApi.updateAudioTrack(project.id, track.id, {
        label: String(data.get('label') ?? track.label),
        scene_id: data.get('scene_id') || null,
        start_ms: Number(data.get('start') ?? 0) * 1000,
        duration_ms: Number(data.get('duration') ?? 0) > 0
          ? Number(data.get('duration')) * 1000
          : null,
        trim_start_ms: Number(data.get('trim') ?? 0) * 1000,
        volume: Number(data.get('volume') ?? 1),
        fade_in_ms: Number(data.get('fade_in') ?? 0) * 1000,
        fade_out_ms: Number(data.get('fade_out') ?? 0) * 1000,
        is_muted: data.get('muted') === 'on',
        asset_file_id: assetFileId,
      })
    }, 'Mixagem da faixa atualizada.')
  }

  async function createCaption(data: FormData) {
    if (!project) return
    await execute(async () => {
      await animeStudioApi.createCaption(project.id, {
        scene_id: data.get('scene_id') || null,
        language: 'pt-BR',
        cue_order: project.captions.length + 1,
        start_ms: Number(data.get('start') ?? 0) * 1000,
        end_ms: Number(data.get('end') ?? 2) * 1000,
        text: String(data.get('text') ?? ''),
        speaker: String(data.get('speaker') ?? ''),
        cue_kind: String(data.get('kind') ?? 'dialogue'),
      })
    }, 'Legenda adicionada.')
  }

  async function updateCaption(cue: AnimeCaptionCue, data: FormData) {
    if (!project) return
    await execute(async () => {
      await animeStudioApi.updateCaption(project.id, cue.id, {
        scene_id: data.get('scene_id') || null,
        language: 'pt-BR',
        start_ms: Number(data.get('start') ?? 0) * 1000,
        end_ms: Number(data.get('end') ?? 0) * 1000,
        text: String(data.get('text') ?? ''),
        speaker: String(data.get('speaker') ?? ''),
        cue_kind: String(data.get('kind') ?? 'dialogue'),
      })
    }, 'Legenda atualizada e sincronizada.')
  }

  async function importCaptions(data: FormData) {
    if (!project) return
    const file = data.get('caption_file')
    if (!(file instanceof File) || !file.size) return
    await execute(async () => {
      const imported = parseCaptionFile(await file.text())
      if (!imported.length) throw new Error('O arquivo não possui legendas SRT/VTT válidas.')
      const candidates = [
        ...project.captions,
        ...imported.map((cue, index) => ({
          ...cue,
          id: `import-${index}`,
          language: 'pt-BR',
        })),
      ]
      if (overlappingCaptionIds(candidates).size) {
        throw new Error('A importação contém intervalos sobrepostos em pt-BR.')
      }
      const initialOrder = Math.max(0, ...project.captions.map((cue) => cue.cue_order))
      for (const [index, cue] of imported.entries()) {
        await animeStudioApi.createCaption(project.id, {
          scene_id: null,
          language: 'pt-BR',
          cue_order: initialOrder + index + 1,
          ...cue,
        })
      }
    }, `Legendas importadas de ${file.name}.`)
  }

  function exportCaptions(format: 'srt' | 'vtt') {
    if (!project?.captions.length) return
    const content = serializeCaptions(project.captions, format)
    const blob = new Blob([content], { type: format === 'srt' ? 'application/x-subrip' : 'text/vtt' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${project.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.${format}`
    link.click()
    URL.revokeObjectURL(url)
  }

  async function requestRender() {
    if (!project) return
    await execute(async () => {
      const render = await animeStudioApi.requestRender(project.id, project.language)
      setTab('render')
      setNotice(`Render v${render.revision} enviado para a fila.`)
    }, 'Renderização iniciada. Você pode continuar trabalhando.')
  }

  async function reviewRender(render: AnimeRender, decision: 'approved' | 'rejected') {
    if (!project) return
    await execute(
      () => animeStudioApi.reviewRender(project.id, render.id, decision).then(() => undefined),
      decision === 'approved'
        ? 'Vídeo aprovado e preservado no histórico.'
        : 'Render rejeitado; a versão continua disponível para auditoria.',
    )
  }

  async function retryRender(render: AnimeRender) {
    if (!render.background_job_id) return
    await execute(async () => {
      await animeStudioApi.retryRenderJob(render.background_job_id as string)
    }, `Render v${render.revision} reenviado para processamento.`)
  }

  async function restoreRender(render: AnimeRender) {
    if (!project) return
    await execute(async () => {
      await animeStudioApi.restoreRender(project.id, render.id)
    }, `Versão v${render.revision} restaurada como versão ativa.`)
  }

  if (loading && !project && projects.length === 0) {
    return (
      <div className="anime-loading" role="status" aria-live="polite">
        <span />
        <p>Preparando o Estúdio Anime…</p>
      </div>
    )
  }

  return (
    <div className="anime-studio-shell">
      <ProjectRail
        projects={projects}
        selectedId={selectedId}
        onSelect={setSelectedId}
        onCreate={() => setDialogOpen(true)}
      />

      <div className="anime-studio-main">
        <header className="anime-studio-hero">
          <div className="anime-hero-copy">
            <span className="anime-eyebrow">EduCode Motion Lab</span>
            <h1>{project?.title ?? 'Estúdio Anime'}</h1>
            <p>
              {project?.synopsis || 'Crie narrativas educacionais em vídeo com voz, música, efeitos e acessibilidade.'}
            </p>
          </div>
          <div className="anime-hero-actions">
            {project ? (
              <>
                <span className={`anime-status status-${project.status}`}>
                  <i /> {statusLabels[project.status] ?? project.status}
                </span>
                <button
                  type="button"
                  className="anime-button primary"
                  onClick={() => void requestRender()}
                  disabled={busy || project.scenes.length === 0 || project.status === 'rendering'}
                >
                  <span aria-hidden="true">▶</span>
                  Renderizar preview
                </button>
              </>
            ) : (
              <button type="button" className="anime-button primary" onClick={() => setDialogOpen(true)}>
                Criar primeiro anime
              </button>
            )}
          </div>
        </header>

        {error ? <div className="anime-alert error" role="alert">{error}</div> : null}
        {notice ? <div className="anime-alert success" role="status" aria-live="polite">{notice}</div> : null}

        {!project ? (
          <section className="anime-welcome">
            <div className="anime-orbit" aria-hidden="true"><span>▶</span><i /><i /><i /></div>
            <span className="anime-eyebrow">Narrativas que se movem</span>
            <h2>Da ideia ao vídeo educacional</h2>
            <p>Organize cenas, sincronize o áudio, revise legendas e renderize com controle docente.</p>
            <button type="button" className="anime-button primary" onClick={() => setDialogOpen(true)}>Começar uma produção</button>
          </section>
        ) : (
          <>
            <section className="anime-metrics" aria-label="Resumo da produção">
              <article><span>Cenas</span><strong>{project.scenes.length}</strong><small>na timeline</small></article>
              <article><span>Duração</span><strong>{formatDuration(totalDuration)}</strong><small>estimada</small></article>
              <article><span>Áudio</span><strong>{project.audio_tracks.length}</strong><small>faixas</small></article>
              <article><span>Acessibilidade</span><strong>{project.captions.length}</strong><small>legendas</small></article>
            </section>

            <nav className="anime-tabs" aria-label="Ferramentas do Estúdio Anime">
              {([
                ['storyboard', 'Storyboard', '▤'],
                ['generation', 'Gerar mídia', '✦'],
                ['audio', 'Áudio', '♫'],
                ['captions', 'Legendas', 'CC'],
                ['render', 'Render e revisão', '▶'],
              ] as const).map(([value, label, icon]) => (
                <button
                  type="button"
                  key={value}
                  className={tab === value ? 'is-active' : ''}
                  aria-current={tab === value ? 'page' : undefined}
                  onClick={() => setTab(value)}
                >
                  <span aria-hidden="true">{icon}</span>{label}
                </button>
              ))}
            </nav>

            {tab === 'storyboard' ? (
              <section className="anime-workspace">
                <div className="anime-stage-panel">
                  <header>
                    <div>
                      <span className="anime-eyebrow">Monitor de cena</span>
                      <h2>{selectedScene?.title ?? 'Selecione uma cena'}</h2>
                    </div>
                    {selectedScene ? <span>{formatDuration(selectedScene.duration_ms)}</span> : null}
                  </header>
                  <div className={`anime-stage ratio-${project.aspect_ratio.replace(':', '-')}`}>
                    <SecureMedia
                      fileId={selectedScene?.visual_asset_file_id ?? null}
                      title={selectedScene?.title ?? 'Cena'}
                      controls
                    />
                    {selectedScene ? (
                      <div className="anime-stage-overlay">
                        <span>Cena {selectedScene.position}</span>
                        <div>
                          <p>{selectedScene.screenplay_text || 'Roteiro visual ainda não descrito.'}</p>
                          <small>
                            {String(selectedScene.camera_settings.shot_type ?? 'Plano médio')}
                            {' · '}{String(selectedScene.camera_settings.movement ?? 'Câmera estática')}
                            {' · '}{String(selectedScene.transition_settings.type ?? 'Corte')}
                          </small>
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>

                <form className="anime-inspector" onSubmit={(event) => {
                  event.preventDefault()
                  void createScene(new FormData(event.currentTarget))
                  event.currentTarget.reset()
                }}>
                  <header><span className="anime-eyebrow">Nova cena</span><h2>Direção visual</h2></header>
                  <label>Título<input name="title" required placeholder="O desafio aparece" /></label>
                  <label>Imagem ou vídeo<input name="media" type="file" required accept="image/png,image/jpeg,image/webp,video/mp4,video/webm,video/quicktime" /></label>
                  <div className="anime-form-grid">
                    <label>Duração (s)<input name="duration" type="number" min="1" max="600" defaultValue="5" /></label>
                    <label>Câmera<select name="camera"><option value="static">Estática</option><option value="pan">Panorâmica</option><option value="zoom_in">Zoom in</option><option value="zoom_out">Zoom out</option></select></label>
                  </div>
                  <label>Enquadramento<select name="shot"><option value="wide">Plano geral</option><option value="medium">Plano médio</option><option value="close_up">Close-up</option><option value="detail">Plano detalhe</option></select></label>
                  <label>Transição<select name="transition"><option value="cut">Corte</option><option value="fade">Fade</option><option value="dissolve">Dissolver</option></select></label>
                  <label>Roteiro<textarea name="screenplay" rows={3} placeholder="A personagem observa o padrão..." /></label>
                  <label>Prompt visual<textarea name="prompt" rows={3} placeholder="Anime escolar, luz suave, plano médio..." /></label>
                  <label className="anime-check-row"><input type="checkbox" required /> Confirmo os direitos de uso da mídia</label>
                  <button className="anime-button primary" disabled={busy} type="submit">Adicionar à timeline</button>
                </form>
              </section>
            ) : null}

            {tab === 'storyboard' ? (
              <section className="anime-timeline-section">
                <header><div><span className="anime-eyebrow">Timeline</span><h2>Sequência de cenas</h2></div><small>Use clique ou teclado para navegar.</small></header>
                <form className="anime-storyboard-import" onSubmit={(event) => {
                  event.preventDefault()
                  void importStoryboard(new FormData(event.currentTarget))
                }}>
                  <label htmlFor="anime-comic-id">Converter HQ em storyboard</label>
                  <input id="anime-comic-id" name="comic_id" type="text" required placeholder="ID da HQ gerada" />
                  <button className="anime-button ghost" disabled={busy} type="submit">Importar cenas</button>
                  <small>Cada quadro vira uma cena; novas importações ignoram quadros já sincronizados.</small>
                </form>
                {selectedScene ? (
                  <div className="anime-scene-properties">
                    <form key={selectedScene.id} onSubmit={(event) => {
                      event.preventDefault()
                      void saveSceneProperties(new FormData(event.currentTarget))
                    }}>
                      <label>Título<input name="title" defaultValue={selectedScene.title} required /></label>
                      <label>Duração (s)<input name="duration" type="number" min="0.5" max="600" step="0.5" defaultValue={selectedScene.duration_ms / 1000} /></label>
                      <label>Plano<select name="shot" defaultValue={String(selectedScene.camera_settings.shot_type ?? 'medium')}><option value="wide">Geral</option><option value="medium">Médio</option><option value="close_up">Close-up</option><option value="detail">Detalhe</option></select></label>
                      <label>Câmera<select name="camera" defaultValue={String(selectedScene.camera_settings.movement ?? 'static')}><option value="static">Estática</option><option value="pan">Panorâmica</option><option value="zoom_in">Zoom in</option><option value="zoom_out">Zoom out</option></select></label>
                      <label>Transição<select name="transition" defaultValue={String(selectedScene.transition_settings.type ?? 'cut')}><option value="cut">Corte</option><option value="fade">Fade</option><option value="dissolve">Dissolver</option></select></label>
                      <button type="submit" className="anime-button primary" disabled={busy}>Salvar cena</button>
                    </form>
                    <div className="anime-timeline-actions" aria-label="Reordenar cena selecionada">
                      <button type="button" className="anime-button ghost" disabled={busy || selectedScene.position === 1} onClick={() => void moveScene(selectedScene.id, -1)}>← Mover antes</button>
                      <button type="button" className="anime-button ghost" disabled={busy || selectedScene.position === project.scenes.length} onClick={() => void moveScene(selectedScene.id, 1)}>Mover depois →</button>
                    </div>
                    <form className="anime-split-scene" onSubmit={(event) => {
                      event.preventDefault()
                      void splitSelectedScene(new FormData(event.currentTarget))
                    }}>
                      <label>Dividir em (s)<input name="split_at" type="number" min="0.5" max={(selectedScene.duration_ms - 500) / 1000} step="0.5" defaultValue={Math.max(0.5, Math.floor(selectedScene.duration_ms / 2000))} /></label>
                      <button type="submit" className="anime-button ghost" disabled={busy || selectedScene.duration_ms < 1000}>Dividir cena</button>
                    </form>
                  </div>
                ) : null}
                {project.scenes.length ? (
                  <div className="anime-scene-strip" role="list">
                    {project.scenes.map((scene: AnimeScene) => (
                      <button
                        type="button"
                        role="listitem"
                        draggable
                        key={scene.id}
                        className={scene.id === selectedSceneId ? 'is-active' : ''}
                        onClick={() => setSelectedSceneId(scene.id)}
                        onDragStart={() => setDraggedSceneId(scene.id)}
                        onDragOver={(event) => event.preventDefault()}
                        onDrop={() => void dropScene(scene.id)}
                        aria-label={`Cena ${scene.position}: ${scene.title}. Arraste para reordenar.`}
                      >
                        <div className="anime-scene-thumb"><SecureMedia fileId={scene.visual_asset_file_id} title={scene.title} /></div>
                        <span><b>{String(scene.position).padStart(2, '0')}</b><strong>{scene.title}</strong><small>{formatDuration(scene.duration_ms)}</small></span>
                        <em>{String(scene.camera_settings.shot_type ?? 'medium')} · {String(scene.camera_settings.movement ?? 'static')}</em>
                      </button>
                    ))}
                  </div>
                ) : <div className="anime-empty-state"><span aria-hidden="true">▤</span><h3>A timeline está vazia</h3><p>Adicione a primeira cena usando o painel de direção visual.</p></div>}
              </section>
            ) : null}

            {tab === 'generation' ? (
              <section className="anime-tool-grid anime-generation-grid">
                <div className="anime-generation-board">
                  <header>
                    <div><span className="anime-eyebrow">Fila de produção</span><h2>Mídia gerada por IA</h2></div>
                    <span>{mediaGenerations.length} solicitações</span>
                  </header>
                  {mediaGenerations.length ? mediaGenerations.map((job) => (
                    <article className="anime-generation-job" key={job.id}>
                      <div className="anime-generation-heading">
                        <span aria-hidden="true">✦</span>
                        <div>
                          <strong>{generationLabels[job.kind]}</strong>
                          <small>{statusLabels[job.status] ?? job.status} · custo estimado US$ {job.estimated_cost.toFixed(4)}</small>
                        </div>
                        <b>{job.progress_percent}%</b>
                      </div>
                      <div className="anime-progress" aria-label={`${job.progress_percent}% concluído`}><i style={{ width: `${job.progress_percent}%` }} /></div>
                      {job.output_asset_file_id ? (
                        <div className="anime-generation-preview">
                          <SecureMedia fileId={job.output_asset_file_id} title={generationLabels[job.kind]} controls />
                        </div>
                      ) : null}
                      <p>{job.error_message || job.current_step}</p>
                      {job.status === 'completed' && job.review_decision === 'pending' ? (
                        <footer>
                          <button type="button" className="anime-button ghost" disabled={busy} onClick={() => void reviewMediaGeneration(job, 'rejected')}>Solicitar nova versão</button>
                          <button type="button" className="anime-button primary" disabled={busy} onClick={() => void reviewMediaGeneration(job, 'approved')}>Aprovar mídia</button>
                        </footer>
                      ) : <small>Revisão: {job.review_decision === 'pending' ? 'aguardando resultado' : job.review_decision}{job.provider ? ` · ${job.provider}` : ''}</small>}
                    </article>
                  )) : <div className="anime-empty-state"><span aria-hidden="true">✦</span><h3>Nenhuma mídia solicitada</h3><p>Escolha o tipo, a cena e envie uma direção criativa.</p></div>}
                </div>

                <form className="anime-inspector" onSubmit={(event) => {
                  event.preventDefault()
                  void requestMediaGeneration(new FormData(event.currentTarget))
                }}>
                  <header><span className="anime-eyebrow">Nova geração</span><h2>Direção de mídia</h2></header>
                  <label>Tipo<select name="kind"><option value="image">Imagem</option><option value="animation">Animação</option><option value="voice">Voz</option><option value="lip_sync">Sincronização labial</option><option value="music">Trilha sonora</option><option value="sfx">Efeito sonoro</option></select></label>
                  <label>Cena<select name="scene_id"><option value="">Produção inteira (trilha/efeito)</option>{project.scenes.map((scene) => <option value={scene.id} key={scene.id}>Cena {scene.position} · {scene.title}</option>)}</select></label>
                  <label>Duração (s)<input name="duration" type="number" min="0.5" max="600" step="0.5" defaultValue="5" /></label>
                  <label>Voz/personagem<input name="voice_name" placeholder="Luna · voz jovem" /></label>
                  <label>Direção criativa<textarea name="prompt" rows={6} placeholder="Anime escolar, movimento suave, voz acolhedora..." /></label>
                  <small>O custo será reservado na quota institucional antes do processamento.</small>
                  <button type="submit" className="anime-button primary" disabled={busy}>Enviar para a fila</button>
                </form>
              </section>
            ) : null}

            {tab === 'audio' ? (
              <section className="anime-tool-grid">
                <div className="anime-track-board">
                  <header><div><span className="anime-eyebrow">Mixer</span><h2>Voz, música e efeitos</h2></div><span>{project.audio_tracks.length} faixas</span></header>
                  {project.audio_tracks.length ? project.audio_tracks.map((track) => (
                    <article className={`anime-track kind-${track.track_kind}${track.is_muted ? ' is-muted' : ''}`} key={track.id}>
                      <div className="anime-track-main">
                        <span className="anime-track-icon" aria-hidden="true">{track.track_kind === 'music' ? '♫' : track.track_kind === 'sfx' ? '✦' : '◉'}</span>
                        <div><strong>{track.label}</strong><small>{trackLabels[track.track_kind]} · inicia em {formatDuration(track.start_ms)}{track.is_muted ? ' · silenciada' : ''}</small>{track.transcript ? <p>{track.transcript}</p> : null}</div>
                        <SecureMedia fileId={track.asset_file_id} title={track.label} controls />
                        <button type="button" className="anime-icon-button danger" aria-label={`Excluir ${track.label}`} onClick={() => void execute(() => animeStudioApi.deleteAudioTrack(project.id, track.id), 'Faixa removida.')}>×</button>
                      </div>
                      <div className="anime-waveform" role="img" aria-label={`Forma de onda de ${track.label}`}>
                        {Array.from({ length: 28 }, (_, index) => <i key={index} style={{ height: `${28 + ((index * 17 + track.label.length * 7) % 68)}%` }} />)}
                      </div>
                      <form className="anime-track-mixer" onSubmit={(event) => { event.preventDefault(); void updateAudio(track, new FormData(event.currentTarget)) }}>
                        <label>Nome<input name="label" defaultValue={track.label} required /></label>
                        <label>Cena<select name="scene_id" defaultValue={track.scene_id ?? ''}><option value="">Produção inteira</option>{project.scenes.map((scene) => <option value={scene.id} key={scene.id}>Cena {scene.position} · {scene.title}</option>)}</select></label>
                        <label>Início (s)<input name="start" type="number" min="0" step="0.1" defaultValue={track.start_ms / 1000} /></label>
                        <label>Duração/corte (s)<input name="duration" type="number" min="0" step="0.1" defaultValue={track.duration_ms ? track.duration_ms / 1000 : ''} placeholder="Original" /></label>
                        <label>Recorte inicial (s)<input name="trim" type="number" min="0" step="0.1" defaultValue={track.trim_start_ms / 1000} /></label>
                        <label>Volume<input name="volume" type="number" min="0" max="2" step="0.05" defaultValue={track.volume} /></label>
                        <label>Fade in (s)<input name="fade_in" type="number" min="0" step="0.1" defaultValue={track.fade_in_ms / 1000} /></label>
                        <label>Fade out (s)<input name="fade_out" type="number" min="0" step="0.1" defaultValue={track.fade_out_ms / 1000} /></label>
                        <label className="anime-track-replacement">Substituir áudio<input name="replacement" type="file" accept="audio/mpeg,audio/wav,audio/ogg,audio/mp4,audio/aac,audio/flac,audio/webm" /></label>
                        <label className="anime-check-row"><input name="muted" type="checkbox" defaultChecked={track.is_muted} /> Silenciar faixa</label>
                        <button type="submit" className="anime-button ghost" disabled={busy}>Salvar mixagem</button>
                      </form>
                    </article>
                  )) : <div className="anime-empty-state"><span aria-hidden="true">♫</span><h3>O anime ainda está silencioso</h3><p>Adicione diálogos, narração, música ou efeitos sonoros.</p></div>}
                </div>
                <form className="anime-inspector" onSubmit={(event) => { event.preventDefault(); void createAudio(new FormData(event.currentTarget)); event.currentTarget.reset() }}>
                  <header><span className="anime-eyebrow">Nova faixa</span><h2>Sincronizar áudio</h2></header>
                  <label>Nome<input name="label" required placeholder="Narração de abertura" /></label>
                  <div className="anime-form-grid"><label>Tipo<select name="kind"><option value="dialogue">Diálogo</option><option value="narration">Narração</option><option value="music">Música</option><option value="sfx">Efeito</option><option value="audio_description">Audiodescrição</option></select></label><label>Início (s)<input name="start" type="number" min="0" step="0.1" defaultValue="0" /></label></div>
                  <label>Cena<select name="scene_id"><option value="">Produção inteira</option>{project.scenes.map((scene) => <option value={scene.id} key={scene.id}>Cena {scene.position} · {scene.title}</option>)}</select></label>
                  <label>Arquivo de áudio<input name="audio" type="file" accept="audio/mpeg,audio/wav,audio/ogg,audio/mp4,audio/aac,audio/flac,audio/webm" required /></label>
                  <label>Personagem/locutor<input name="speaker" placeholder="Luna" /></label>
                  <label>Transcrição<textarea name="transcript" rows={4} /></label>
                  <label>Volume<input name="volume" type="range" min="0" max="2" step="0.05" defaultValue="1" /></label>
                  <label className="anime-check-row"><input type="checkbox" required /> Confirmo os direitos de uso do áudio</label>
                  <button type="submit" className="anime-button primary" disabled={busy}>Adicionar faixa</button>
                </form>
              </section>
            ) : null}

            {tab === 'captions' ? (
              <section className="anime-tool-grid">
                <div className="anime-caption-board">
                  <header><div><span className="anime-eyebrow">Acessibilidade</span><h2>Legendas e sons importantes</h2></div><span>pt-BR</span></header>
                  <div className="anime-caption-preview">
                    <SecureMedia fileId={activeRender?.output_asset_file_id ?? selectedScene?.visual_asset_file_id ?? null} title="Preview sincronizado das legendas" controls />
                    <div className={`anime-caption-overlay${activeCaption ? ' is-active' : ''}`} aria-live="polite">
                      {activeCaption ? <><strong>{activeCaption.speaker}</strong><span>{activeCaption.text}</span></> : <span>Sem legenda neste instante</span>}
                    </div>
                  </div>
                  <label className="anime-caption-scrubber">Posição do preview · {formatDuration(captionPreviewMs)}<input type="range" min="0" max={Math.max(1000, totalDuration, ...project.captions.map((cue) => cue.end_ms))} step="100" value={captionPreviewMs} onChange={(event) => setCaptionPreviewMs(Number(event.target.value))} /></label>
                  {captionConflicts.size ? <div className="anime-alert error" role="alert">Há {captionConflicts.size} legendas com intervalos sobrepostos. Ajuste os tempos destacados.</div> : null}
                  {project.captions.length ? <ol>{[...project.captions].sort((a, b) => a.start_ms - b.start_ms).map((cue) => (
                    <li className={captionConflicts.has(cue.id) ? 'has-conflict' : ''} key={cue.id}>
                      <form className="anime-caption-editor" onSubmit={(event) => { event.preventDefault(); void updateCaption(cue, new FormData(event.currentTarget)) }}>
                        <label>Início (s)<input name="start" type="number" min="0" step="0.1" defaultValue={cue.start_ms / 1000} required /></label>
                        <label>Fim (s)<input name="end" type="number" min="0.1" step="0.1" defaultValue={cue.end_ms / 1000} required /></label>
                        <label>Cena<select name="scene_id" defaultValue={cue.scene_id ?? ''}><option value="">Produção inteira</option>{project.scenes.map((scene) => <option value={scene.id} key={scene.id}>Cena {scene.position} · {scene.title}</option>)}</select></label>
                        <label>Tipo<select name="kind" defaultValue={cue.cue_kind}><option value="dialogue">Diálogo</option><option value="narration">Narração</option><option value="sound">Som importante</option><option value="audio_description">Audiodescrição</option></select></label>
                        <label>Locutor<input name="speaker" defaultValue={cue.speaker} /></label>
                        <label className="anime-caption-text">Texto<textarea name="text" rows={2} defaultValue={cue.text} required /></label>
                        <button type="submit" className="anime-button ghost" disabled={busy}>Salvar</button>
                        <button type="button" className="anime-icon-button danger" aria-label={`Excluir legenda ${cue.cue_order}`} onClick={() => void execute(() => animeStudioApi.deleteCaption(project.id, cue.id), 'Legenda removida.')}>×</button>
                      </form>
                    </li>
                  ))}</ol> : <div className="anime-empty-state"><span aria-hidden="true">CC</span><h3>Sem legendas</h3><p>Inclua falas, narração e descrições de sons relevantes.</p></div>}
                </div>
                <form className="anime-inspector" onSubmit={(event) => { event.preventDefault(); void createCaption(new FormData(event.currentTarget)); event.currentTarget.reset() }}>
                  <header><span className="anime-eyebrow">Novo trecho</span><h2>Adicionar legenda</h2></header>
                  <label>Cena<select name="scene_id"><option value="">Produção inteira</option>{project.scenes.map((scene) => <option value={scene.id} key={scene.id}>Cena {scene.position} · {scene.title}</option>)}</select></label>
                  <div className="anime-form-grid"><label>Início (s)<input name="start" type="number" min="0" step="0.1" required /></label><label>Fim (s)<input name="end" type="number" min="0.1" step="0.1" required /></label></div>
                  <label>Tipo<select name="kind"><option value="dialogue">Diálogo</option><option value="narration">Narração</option><option value="sound">Som importante</option><option value="audio_description">Audiodescrição</option></select></label>
                  <label>Personagem/locutor<input name="speaker" /></label>
                  <label>Texto<textarea name="text" rows={5} required placeholder="[Som de chuva] ou fala do personagem" /></label>
                  <button type="submit" className="anime-button primary" disabled={busy}>Adicionar legenda</button>
                  <hr />
                  <header><span className="anime-eyebrow">Interoperabilidade</span><h2>SRT e WebVTT</h2></header>
                  <label>Arquivo de legendas<input name="caption_file" type="file" accept=".srt,.vtt,text/vtt,application/x-subrip" /></label>
                  <button type="button" className="anime-button ghost" disabled={busy} onClick={(event) => { const form = event.currentTarget.form; if (form) void importCaptions(new FormData(form)) }}>Importar SRT/VTT</button>
                  <div className="anime-caption-export"><button type="button" className="anime-button ghost" onClick={() => exportCaptions('srt')} disabled={!project.captions.length}>Exportar SRT</button><button type="button" className="anime-button ghost" onClick={() => exportCaptions('vtt')} disabled={!project.captions.length}>Exportar VTT</button></div>
                </form>
              </section>
            ) : null}

            {tab === 'render' ? (
              <section className="anime-render-grid">
                <div className="anime-render-player">
                  <header><div><span className="anime-eyebrow">Preview protegido</span><h2>{selectedRender ? `Render v${selectedRender.revision}` : 'Nenhum render'}</h2></div>{selectedRender ? <span className={`anime-status status-${selectedRender.status}`}><i />{statusLabels[selectedRender.status] ?? selectedRender.status}</span> : null}</header>
                  <div className="anime-video-frame"><SecureMedia fileId={selectedRender?.output_asset_file_id ?? null} title={`Render de ${project.title}`} controls />{selectedRenderJob && !['completed', 'failed', 'cancelled'].includes(selectedRenderJob.status) ? <div className="anime-rendering-overlay" role="status"><span /><strong>{selectedRenderJob.current_step}</strong><small>{selectedRenderJob.progress_percent}% · tentativa {selectedRenderJob.retry_count + 1} de {selectedRenderJob.max_retries + 1}</small></div> : null}</div>
                  {selectedRenderJob ? <div className="anime-render-progress" aria-label={`Progresso do render ${selectedRenderJob.progress_percent}%`}><div><span>{selectedRenderJob.current_step}</span><strong>{selectedRenderJob.progress_percent}%</strong></div><div className="anime-progress"><i style={{ width: `${selectedRenderJob.progress_percent}%` }} /></div></div> : null}
                  {selectedRender?.error_message ? <div className="anime-alert error" role="alert">{selectedRender.error_message}</div> : null}
                  {selectedRender?.status === 'in_review' ? <div className="anime-review-actions"><div><strong>Decisão humana obrigatória</strong><p>Assista ao vídeo completo antes de aprovar a publicação.</p></div><button type="button" className="anime-button ghost danger" onClick={() => void reviewRender(selectedRender, 'rejected')} disabled={busy}>Solicitar ajustes</button><button type="button" className="anime-button primary" onClick={() => void reviewRender(selectedRender, 'approved')} disabled={busy}>Aprovar versão</button></div> : null}
                  {project.renders.length > 1 ? <section className="anime-render-comparison"><header><div><span className="anime-eyebrow">Comparação</span><h2>Conferir duas versões</h2></div><select aria-label="Versão para comparar" value={comparisonRenderId ?? ''} onChange={(event) => setComparisonRenderId(event.target.value || null)}><option value="">Selecione outra versão</option>{project.renders.filter((render) => render.id !== selectedRender?.id).map((render) => <option value={render.id} key={render.id}>Versão {render.revision}</option>)}</select></header>{comparisonRender ? <div><article><strong>v{selectedRender?.revision}</strong><SecureMedia fileId={selectedRender?.output_asset_file_id ?? null} title={`Versão ${selectedRender?.revision}`} controls /></article><article><strong>v{comparisonRender.revision}</strong><SecureMedia fileId={comparisonRender.output_asset_file_id} title={`Versão ${comparisonRender.revision}`} controls /></article></div> : <p>Escolha uma versão no campo acima para comparar os previews lado a lado.</p>}</section> : null}
                </div>
                <aside className="anime-render-history"><header><span className="anime-eyebrow">Histórico imutável</span><h2>Versões</h2></header>{project.renders.length ? <ol>{[...project.renders].sort((a, b) => b.revision - a.revision).map((render) => { const job = render.background_job_id ? renderJobs[render.background_job_id] : undefined; const isActive = String(project.production_notes.active_render_id ?? '') === render.id; return <li className={`${selectedRender?.id === render.id ? 'is-selected' : ''}${isActive ? ' is-active' : ''}`} key={render.id}><button type="button" className="anime-render-version" onClick={() => setSelectedRenderId(render.id)}><span>v{render.revision}</span><div><strong>{statusLabels[render.status] ?? render.status}{isActive ? ' · ativa' : ''}</strong><small>{job?.current_step ?? new Date(render.created_at).toLocaleString('pt-BR')}</small>{job ? <div className="anime-progress"><i style={{ width: `${job.progress_percent}%` }} /></div> : null}</div><em>{formatDuration(render.duration_ms)}</em></button><div className="anime-render-version-actions">{render.status === 'failed' && render.background_job_id ? <button type="button" className="anime-button ghost" disabled={busy} onClick={() => void retryRender(render)}>Reprocessar</button> : null}{render.status === 'approved' && !isActive ? <button type="button" className="anime-button ghost" disabled={busy} onClick={() => void restoreRender(render)}>Restaurar</button> : null}</div></li> })}</ol> : <div className="anime-empty-state compact"><span aria-hidden="true">▶</span><p>O primeiro render aparecerá aqui.</p></div>}<button type="button" className="anime-button primary full" onClick={() => void requestRender()} disabled={busy || !project.scenes.length || project.status === 'rendering'}>Gerar novo preview</button><p className="anime-governance-note">A IA pode ajudar na criação, mas nenhuma versão é publicada sem aprovação docente.</p></aside>
              </section>
            ) : null}
          </>
        )}
      </div>

      <CreateProjectDialog open={dialogOpen} onClose={() => setDialogOpen(false)} onSubmit={createProject} busy={busy} />
    </div>
  )
}
