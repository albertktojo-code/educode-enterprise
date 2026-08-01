import { api, apiBlob } from '../../lib/api'
import type {
  AnimeAudioTrack,
  AnimeCaptionCue,
  AnimeMediaUpload,
  AnimeProject,
  AnimeProjectSummary,
  AnimeRender,
  AnimeScene,
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
  updateScene: (projectId: string, sceneId: string, input: Record<string, unknown>) =>
    api.patch<AnimeScene>(
      `/anime-studio/projects/${projectId}/scenes/${sceneId}`,
      input,
    ),
  deleteScene: (projectId: string, sceneId: string) =>
    api.delete<void>(`/anime-studio/projects/${projectId}/scenes/${sceneId}`),
  createAudioTrack: (projectId: string, input: Record<string, unknown>) =>
    api.post<AnimeAudioTrack>(
      `/anime-studio/projects/${projectId}/audio-tracks`,
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
