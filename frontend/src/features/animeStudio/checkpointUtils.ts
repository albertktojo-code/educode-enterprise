import type { AnimeInteractiveCheckpoint, AnimeProject } from './types'

export function readProjectCheckpoints(
  project: AnimeProject,
): AnimeInteractiveCheckpoint[] {
  const value = project.production_notes.interactive_checkpoints
  if (!Array.isArray(value)) return []
  return value
    .filter((item): item is AnimeInteractiveCheckpoint => {
      if (!item || typeof item !== 'object') return false
      const checkpoint = item as Partial<AnimeInteractiveCheckpoint>
      return (
        typeof checkpoint.id === 'string'
        && typeof checkpoint.timestamp_ms === 'number'
        && typeof checkpoint.label === 'string'
        && typeof checkpoint.assignment_id === 'string'
        && typeof checkpoint.pause_playback === 'boolean'
        && typeof checkpoint.required === 'boolean'
      )
    })
    .sort((left, right) => left.timestamp_ms - right.timestamp_ms)
}
