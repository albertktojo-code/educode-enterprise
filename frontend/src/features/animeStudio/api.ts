import { api, apiBlob } from '../../lib/api'
import type {
  AnimeAudioTrack,
  AnimeCaptionCue,
  AnimeMediaUpload,
  AnimeMediaGeneration,
  AnimeMediaGenerationKind,
  AnimeProject,
  AnimeProjectSummary,
  AnimeRender,
  AnimeScene,
  AnimeStoryboardImportResult,
} from './types'

export interface CreateAnimeProjectInput {
  title: string
  synopsis: string
  style_preset_code: string
  aspect_ratio: '16:9' | '9:16' | '1:1' | '4:3'
  width: number
  height: number
  fps: number
  language: string
  accessibility_options: Record<string, unknown>
}

export const animeStudioApi = {
  listProjects: () => api.get<AnimeProjectSummary[]>('/anime-studio/projects'),
  getProject: (projectId: string) =>
    api.get<AnimeProject>(`/anime-studio/projects/${projectId}`),
  createProject: (input: CreateAnimeProjectInput) =>
    api.post<AnimeProject>('/anime-studio/projects', input),
  updateProject: (projectId: string, input: Record<string, unknown>) =>
    api.patch<AnimeProject>(`/anime-studio/projects/${projectId}`, input),
  createScene: (projectId: string, input: Record<string, unknown>) =>
    api.post<AnimeScene>(`/anime-studio/projects/${projectId}/scenes`, input),
  importStoryboard: (projectId: string, comicId: string) =>
    api.post<AnimeStoryboardImportResult>(
      `/anime-studio/projects/${projectId}/storyboard/from-comic`,
      { comic_id: comicId },
    ),
  listMediaGenerations: (projectId: string) =>
    api.get<AnimeMediaGeneration[]>(
      `/anime-studio/projects/${projectId}/media-generations`,
    ),
  requestMediaGeneration: (
    projectId: string,
    input: {
      scene_id: string | null
      kind: AnimeMediaGenerationKind
      prompt: string
      duration_ms: number
      voice_name: string
    },
  ) => api.post<AnimeMediaGeneration>(
    `/anime-studio/projects/${projectId}/media-generations`,
    input,
  ),
  reviewMediaGeneration: (
    projectId: string,
    jobId: string,
    decision: 'approved' | 'rejected',
  ) => api.post<AnimeMediaGeneration>(
    `/anime-studio/projects/${projectId}/media-generations/${jobId}/review`,
    { decision, notes: '' },
  ),
  updateScene: (projectId: string, sceneId: string, input: Record<string, unknown>) =>
    api.patch<AnimeScene>(
      `/anime-studio/projects/${projectId}/scenes/${sceneId}`,
      input,
    ),
  reorderTimeline: (projectId: string, sceneIds: string[]) =>
    api.put<AnimeProject>(`/anime-studio/projects/${projectId}/timeline`, {
      scene_ids: sceneIds,
    }),
  splitScene: (projectId: string, sceneId: string, splitAtMs: number) =>
    api.post<{ first: AnimeScene; second: AnimeScene }>(
      `/anime-studio/projects/${projectId}/scenes/${sceneId}/split`,
      { split_at_ms: splitAtMs },
    ),
  deleteScene: (projectId: string, sceneId: string) =>
    api.delete<void>(`/anime-studio/projects/${projectId}/scenes/${sceneId}`),
  createAudioTrack: (projectId: string, input: Record<string, unknown>) =>
    api.post<AnimeAudioTrack>(
      `/anime-studio/projects/${projectId}/audio-tracks`,
      input,
    ),
  updateAudioTrack: (
    projectId: string,
    trackId: string,
    input: Record<string, unknown>,
  ) => api.patch<AnimeAudioTrack>(
    `/anime-studio/projects/${projectId}/audio-tracks/${trackId}`,
    input,
  ),
  deleteAudioTrack: (projectId: string, trackId: string) =>
    api.delete<void>(
      `/anime-studio/projects/${projectId}/audio-tracks/${trackId}`,
    ),
  createCaption: (projectId: string, input: Record<string, unknown>) =>
    api.post<AnimeCaptionCue>(
      `/anime-studio/projects/${projectId}/captions`,
      input,
    ),
  deleteCaption: (projectId: string, cueId: string) =>
    api.delete<void>(`/anime-studio/projects/${projectId}/captions/${cueId}`),
  requestRender: (projectId: string, captionLanguage: string) =>
    api.post<AnimeRender>(`/anime-studio/projects/${projectId}/renders`, {
      burn_captions: true,
      caption_language: captionLanguage,
      quality: 'preview',
      normalize_audio: true,
    }),
  reviewRender: (
    projectId: string,
    renderId: string,
    decision: 'approved' | 'rejected',
    notes = '',
  ) =>
    api.post<AnimeRender>(
      `/anime-studio/projects/${projectId}/renders/${renderId}/review`,
      { decision, notes },
    ),
  uploadMedia: async (
    projectId: string,
    file: File,
    mediaKind: 'image' | 'video' | 'audio',
    title: string,
  ) => {
    const form = new FormData()
    form.set('file', file)
    form.set('media_kind', mediaKind)
    form.set('title', title)
    form.set('rights_confirmed', 'true')
    form.set('project_id', projectId)
    return api<AnimeMediaUpload>('/anime-studio/media', {
      method: 'POST',
      body: form,
    })
  },
  mediaBlob: (fileId: string) => apiBlob(`/anime-studio/media/${fileId}`),
}
