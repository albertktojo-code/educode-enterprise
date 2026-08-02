import type { AnimeCaptionCue } from './types'

export interface CaptionFileCue {
  start_ms: number
  end_ms: number
  text: string
  speaker: string
  cue_kind: AnimeCaptionCue['cue_kind']
}

function parseTimestamp(value: string): number {
  const match = value.trim().match(/(?:(\d+):)?(\d{2}):(\d{2})[,.](\d{3})/)
  if (!match) throw new Error(`Tempo de legenda inválido: ${value}`)
  return (
    Number(match[1] ?? 0) * 3_600_000 +
    Number(match[2]) * 60_000 +
    Number(match[3]) * 1000 +
    Number(match[4])
  )
}

function formatTimestamp(milliseconds: number, separator: ',' | '.'): string {
  const hours = Math.floor(milliseconds / 3_600_000)
  const minutes = Math.floor((milliseconds % 3_600_000) / 60_000)
  const seconds = Math.floor((milliseconds % 60_000) / 1000)
  const millis = milliseconds % 1000
  return [hours, minutes, seconds]
    .map((value) => String(value).padStart(2, '0'))
    .join(':') + separator + String(millis).padStart(3, '0')
}

export function parseCaptionFile(source: string): CaptionFileCue[] {
  const normalized = source.replace(/^\uFEFF/, '').replace(/\r/g, '').trim()
  const blocks = normalized
    .replace(/^WEBVTT[^\n]*\n+/, '')
    .split(/\n{2,}/)
    .map((block) => block.split('\n').filter(Boolean))
  return blocks.flatMap((lines) => {
    const timingIndex = lines.findIndex((line) => line.includes('-->'))
    if (timingIndex < 0) return []
    const [start, endWithSettings] = lines[timingIndex].split('-->')
    const end = endWithSettings.trim().split(/\s+/)[0]
    const rawText = lines.slice(timingIndex + 1).join('\n').trim()
    if (!rawText) return []
    const voiceMatch = rawText.match(/^<v\s+([^>]+)>([\s\S]*)$/i)
    const speakerMatch = rawText.match(/^([^:\n]{1,80}):\s+([\s\S]+)$/)
    const speaker = (voiceMatch?.[1] ?? speakerMatch?.[1] ?? '').trim()
    const text = (voiceMatch?.[2] ?? speakerMatch?.[2] ?? rawText)
      .replace(/<[^>]+>/g, '')
      .trim()
    return [{
      start_ms: parseTimestamp(start),
      end_ms: parseTimestamp(end),
      text,
      speaker,
      cue_kind: /^\[.+\]$/.test(text) ? 'sound' : 'dialogue',
    }]
  })
}

export function serializeCaptions(
  captions: AnimeCaptionCue[],
  format: 'srt' | 'vtt',
): string {
  const separator = format === 'srt' ? ',' : '.'
  const body = [...captions]
    .sort((a, b) => a.start_ms - b.start_ms || a.cue_order - b.cue_order)
    .map((cue, index) => {
      const timing = `${formatTimestamp(cue.start_ms, separator)} --> ${formatTimestamp(cue.end_ms, separator)}`
      const text = cue.speaker ? `${cue.speaker}: ${cue.text}` : cue.text
      return `${index + 1}\n${timing}\n${text}`
    })
    .join('\n\n')
  return format === 'vtt' ? `WEBVTT\n\n${body}\n` : `${body}\n`
}

export function overlappingCaptionIds(
  captions: Pick<AnimeCaptionCue, 'id' | 'language' | 'start_ms' | 'end_ms'>[],
): Set<string> {
  const conflicts = new Set<string>()
  const ordered = [...captions].sort((a, b) => a.start_ms - b.start_ms)
  ordered.forEach((cue, index) => {
    for (let nextIndex = index + 1; nextIndex < ordered.length; nextIndex += 1) {
      const next = ordered[nextIndex]
      if (next.start_ms >= cue.end_ms) break
      if (next.language === cue.language && cue.start_ms < next.end_ms) {
        conflicts.add(cue.id)
        conflicts.add(next.id)
      }
    }
  })
  return conflicts
}
