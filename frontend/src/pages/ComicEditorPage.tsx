import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../lib/api'
import type {
  BalloonType,
  Comic,
  ComicBalloon,
  ComicPage,
  ComicPanel,
  ComicRegenerationProposal,
  CanvasReadiness,
  NarrativeMap,
  RegenerationPolicy,
  StabilityReport,
  ReviewSpecialty,
  ContinuityReport,
  GenerationScope,
  LayoutTemplate,
  PanelShape,
  PanelSize,
} from '../types/comic'

const shapeLabels: Record<PanelShape, string> = {
  rectangle: 'Retangular',
  square: 'Quadrado',
  horizontal: 'Horizontal',
  vertical: 'Vertical',
  circle: 'Circular',
  oval: 'Oval',
  panoramic: 'Panorâmico',
  custom: 'Personalizado',
}

const sizeLabels: Record<PanelSize, string> = {
  small: 'Pequeno',
  medium: 'Médio',
  large: 'Grande',
  full_page: 'Página inteira',
  custom: 'Personalizado',
}

const balloonLabels: Record<BalloonType, string> = {
  speech: 'Fala',
  thought: 'Pensamento',
  shout: 'Grito',
  whisper: 'Sussurro',
  narration: 'Narração',
  caption: 'Legenda',
  pedagogical: 'Explicação pedagógica',
}

function percentage(value: number) {
  return `${Math.round(value)}%`
}

function downloadJson(name: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = name
  anchor.click()
  URL.revokeObjectURL(url)
}

export function ComicEditorPage() {
  const { comicId = '' } = useParams()
  const [comic, setComic] = useState<Comic | null>(null)
  const [templates, setTemplates] = useState<LayoutTemplate[]>([])
  const [continuity, setContinuity] = useState<ContinuityReport | null>(null)
  const [narrativeMap, setNarrativeMap] = useState<NarrativeMap | null>(null)
  const [stability, setStability] = useState<StabilityReport | null>(null)
  const [readiness, setReadiness] = useState<CanvasReadiness | null>(null)
  const [regenPolicy, setRegenPolicy] = useState<RegenerationPolicy | null>(null)
  const [localDraftAvailable, setLocalDraftAvailable] = useState(false)
  const [localDraftSavedAt, setLocalDraftSavedAt] = useState<string | null>(null)
  const [proposals, setProposals] = useState<ComicRegenerationProposal[]>([])
  const [commentText, setCommentText] = useState('')
  const [commentSpecialty, setCommentSpecialty] = useState<ReviewSpecialty>('narrative')
  const [selectedPageId, setSelectedPageId] = useState('')
  const [selectedPanelId, setSelectedPanelId] = useState('')
  const [selectedBalloonId, setSelectedBalloonId] = useState('')
  const [mode, setMode] = useState<'teacher' | 'designer'>('teacher')
  const [regenScope, setRegenScope] = useState<GenerationScope>('panel')
  const [regenInstruction, setRegenInstruction] = useState('')
  const [preserveDialogue, setPreserveDialogue] = useState(false)
  const [preserveScene, setPreserveScene] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [characterName, setCharacterName] = useState('')
  const [characterDestination, setCharacterDestination] = useState<'project' | 'personal' | 'institutional_review'>('personal')

  async function load(preferredPanelId?: string, preferredBalloonId?: string) {
    const [comicData, templateData, continuityData, narrativeData, stabilityData, readinessData] = await Promise.all([
      api<Comic>(`/comics/${comicId}`),
      api<LayoutTemplate[]>('/comics/layout-templates'),
      api<ContinuityReport>(`/comics/${comicId}/continuity`),
      api<NarrativeMap>(`/comics/${comicId}/narrative-map`),
      api<StabilityReport>(`/comics/${comicId}/stability-report`),
      api<CanvasReadiness>(`/comics/${comicId}/canvas-readiness`),
    ])
    setComic(comicData)
    setTemplates(templateData)
    setContinuity(continuityData)
    setNarrativeMap(narrativeData)
    setStability(stabilityData)
    setReadiness(readinessData)
    setProposals(comicData.regeneration_proposals.filter((item) => item.status === 'proposed'))
    const currentPage = comicData.pages.find((page) => page.id === selectedPageId) ?? comicData.pages[0]
    const currentPanel =
      currentPage?.panels.find((panel) => panel.id === preferredPanelId || panel.id === selectedPanelId) ??
      currentPage?.panels[0]
    const currentBalloon =
      currentPanel?.balloons.find((balloon) => balloon.id === preferredBalloonId || balloon.id === selectedBalloonId) ??
      currentPanel?.balloons[0]
    setSelectedPageId(currentPage?.id ?? '')
    setSelectedPanelId(currentPanel?.id ?? '')
    setSelectedBalloonId(currentBalloon?.id ?? '')
  }

  useEffect(() => {
    void load().catch((caughtError) => {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao abrir o editor de HQ.')
    })
  }, [comicId])

  useEffect(() => {
    if (!comic) return undefined
    const timer = window.setInterval(() => {
      void api<Comic>(`/comics/${comicId}/autosave`, {
        method: 'POST',
        body: JSON.stringify({
          client_revision: comic.autosave_revision,
          expected_edit_revision: comic.edit_revision,
          draft_payload: {
            selected_page_id: selectedPageId,
            selected_panel_id: selectedPanelId,
            selected_balloon_id: selectedBalloonId,
            mode,
            regeneration_instruction: regenInstruction,
          },
        }),
      })
        .then((saved) => setComic(saved))
        .catch(() => undefined)
    }, 30000)
    return () => window.clearInterval(timer)
  }, [
    comicId,
    comic?.autosave_revision,
    mode,
    regenInstruction,
    selectedBalloonId,
    selectedPageId,
    selectedPanelId,
  ])

  useEffect(() => {
    const key = `educode_comic_local_draft_${comicId}`
    const stored = localStorage.getItem(key)
    if (!stored) return
    try {
      const parsed = JSON.parse(stored) as { saved_at?: string }
      setLocalDraftAvailable(true)
      setLocalDraftSavedAt(parsed.saved_at ?? null)
    } catch {
      localStorage.removeItem(key)
    }
  }, [comicId])

  useEffect(() => {
    const key = `educode_comic_local_draft_${comicId}`
    let timer: number | undefined
    const capture = () => {
      window.clearTimeout(timer)
      timer = window.setTimeout(() => {
        const forms = Array.from(document.querySelectorAll<HTMLFormElement>('form[data-draft-scope]'))
        const formPayload = forms.map((form) => {
          const values: Record<string, string | boolean> = {}
          for (const element of Array.from(form.elements)) {
            if (!(element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement || element instanceof HTMLSelectElement)) continue
            if (!element.name) continue
            values[element.name] = element instanceof HTMLInputElement && element.type === 'checkbox' ? element.checked : element.value
          }
          return { scope: form.dataset.draftScope ?? '', values }
        })
        localStorage.setItem(key, JSON.stringify({
          saved_at: new Date().toISOString(),
          edit_revision: comic?.edit_revision ?? 0,
          selected_page_id: selectedPageId,
          selected_panel_id: selectedPanelId,
          selected_balloon_id: selectedBalloonId,
          forms: formPayload,
        }))
        setLocalDraftAvailable(true)
        setLocalDraftSavedAt(new Date().toISOString())
      }, 600)
    }
    document.addEventListener('input', capture)
    document.addEventListener('change', capture)
    return () => {
      document.removeEventListener('input', capture)
      document.removeEventListener('change', capture)
      window.clearTimeout(timer)
    }
  }, [comicId, comic?.edit_revision, selectedBalloonId, selectedPageId, selectedPanelId])

  function discardLocalDraft() {
    localStorage.removeItem(`educode_comic_local_draft_${comicId}`)
    setLocalDraftAvailable(false)
    setLocalDraftSavedAt(null)
  }

  function restoreLocalDraft() {
    const stored = localStorage.getItem(`educode_comic_local_draft_${comicId}`)
    if (!stored) return
    try {
      const parsed = JSON.parse(stored) as { forms?: Array<{ scope: string; values: Record<string, string | boolean> }> }
      for (const item of parsed.forms ?? []) {
        const form = document.querySelector<HTMLFormElement>(`form[data-draft-scope="${item.scope}"]`)
        if (!form) continue
        for (const [name, value] of Object.entries(item.values)) {
          const field = form.elements.namedItem(name)
          if (field instanceof HTMLInputElement && field.type === 'checkbox') field.checked = Boolean(value)
          else if (field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement || field instanceof HTMLSelectElement) field.value = String(value)
        }
      }
      setSuccess('Rascunho local restaurado nos campos visíveis. Revise e salve no servidor.')
    } catch {
      setError('Não foi possível restaurar o rascunho local.')
    }
  }

  const selectedPage = useMemo(
    () => comic?.pages.find((page) => page.id === selectedPageId) ?? comic?.pages[0] ?? null,
    [comic, selectedPageId],
  )
  const selectedPanel = useMemo(
    () => selectedPage?.panels.find((panel) => panel.id === selectedPanelId) ?? selectedPage?.panels[0] ?? null,
    [selectedPage, selectedPanelId],
  )
  const selectedBalloon = useMemo(
    () => selectedPanel?.balloons.find((balloon) => balloon.id === selectedBalloonId) ?? selectedPanel?.balloons[0] ?? null,
    [selectedPanel, selectedBalloonId],
  )

  function choosePage(page: ComicPage) {
    setSelectedPageId(page.id)
    setSelectedPanelId(page.panels[0]?.id ?? '')
    setSelectedBalloonId(page.panels[0]?.balloons[0]?.id ?? '')
  }

  function choosePanel(panel: ComicPanel) {
    setSelectedPanelId(panel.id)
    setSelectedBalloonId(panel.balloons[0]?.id ?? '')
  }

  function revisionHeaders(): HeadersInit {
    return comic ? { 'If-Match-Revision': String(comic.edit_revision) } : {}
  }

  async function perform(action: () => Promise<Comic>, message: string) {
    setBusy(true)
    setError('')
    setSuccess('')
    try {
      const updated = await action()
      setComic(updated)
      discardLocalDraft()
      setSuccess(message)
      await load(selectedPanelId, selectedBalloonId)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Não foi possível concluir a edição.')
    } finally {
      setBusy(false)
    }
  }

  async function savePage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedPage) return
    const form = new FormData(event.currentTarget)
    await perform(
      () =>
        api<Comic>(`/comics/${comicId}/pages/${selectedPage.id}`, {
          method: 'PATCH',
          headers: revisionHeaders(),
          body: JSON.stringify({
            page_format: String(form.get('page_format')),
            orientation: String(form.get('orientation')),
            layout_template: String(form.get('layout_template')),
            panel_count: Number(form.get('panel_count')),
            reading_direction: String(form.get('reading_direction')),
            notes: String(form.get('notes') ?? ''),
          }),
        }),
      'Página e composição atualizadas em uma nova versão.',
    )
  }

  async function savePanel(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedPanel) return
    const form = new FormData(event.currentTarget)
    let visualPrompt: Record<string, unknown> | undefined
    const visualPromptText = String(form.get('visual_prompt_json') ?? '').trim()
    if (visualPromptText) {
      try {
        visualPrompt = JSON.parse(visualPromptText) as Record<string, unknown>
      } catch {
        setError('O prompt visual estruturado precisa estar em JSON válido.')
        return
      }
    }
    await perform(
      () =>
        api<Comic>(`/comics/${comicId}/panels/${selectedPanel.id}`, {
          method: 'PATCH',
          headers: revisionHeaders(),
          body: JSON.stringify({
            shape: String(form.get('shape')),
            size_category: String(form.get('size_category')),
            position_x: Number(form.get('position_x')),
            position_y: Number(form.get('position_y')),
            width: Number(form.get('width')),
            height: Number(form.get('height')),
            rotation: Number(form.get('rotation')),
            narrative_goal: String(form.get('narrative_goal')),
            pedagogical_goal: String(form.get('pedagogical_goal')),
            scene_description: String(form.get('scene_description')),
            previous_panel_summary: String(form.get('previous_panel_summary')),
            next_panel_hook: String(form.get('next_panel_hook')),
            emotion: String(form.get('emotion')),
            plot_function: String(form.get('plot_function')),
            pacing: String(form.get('pacing') ?? selectedPanel.pacing),
            text_word_limit: Number(form.get('text_word_limit') ?? selectedPanel.text_word_limit),
            alt_text: String(form.get('alt_text') ?? selectedPanel.alt_text ?? ''),
            audio_description: String(form.get('audio_description') ?? selectedPanel.audio_description ?? ''),
            visual_prompt: visualPrompt ?? selectedPanel.visual_prompt,
          }),
        }),
      'Quadro atualizado. Os quadros seguintes foram sinalizados para revisão de continuidade.',
    )
  }

  async function saveBalloon(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedBalloon) return
    const form = new FormData(event.currentTarget)
    await perform(
      () =>
        api<Comic>(`/comics/${comicId}/balloons/${selectedBalloon.id}`, {
          method: 'PATCH',
          headers: revisionHeaders(),
          body: JSON.stringify({
            speaker_name_snapshot: String(form.get('speaker_name_snapshot') ?? ''),
            balloon_type: String(form.get('balloon_type')),
            text: String(form.get('text')),
            emotion: String(form.get('emotion') ?? ''),
            pedagogical_function: String(form.get('pedagogical_function') ?? ''),
            position_x: Number(form.get('position_x')),
            position_y: Number(form.get('position_y')),
            width: Number(form.get('width')),
            height: Number(form.get('height')),
            is_locked: form.get('is_locked') === 'on',
          }),
        }),
      'Balão corrigido sem regenerar a página inteira.',
    )
  }

  async function addBalloon() {
    if (!selectedPanel) return
    const sequence = Math.max(0, ...selectedPanel.balloons.map((balloon) => balloon.sequence_number)) + 1
    await perform(
      () =>
        api<Comic>(`/comics/${comicId}/panels/${selectedPanel.id}/balloons`, {
          method: 'POST',
          body: JSON.stringify({
            sequence_number: sequence,
            balloon_type: 'speech',
            text: 'Novo diálogo — clique para editar.',
            position_x: sequence % 2 ? 8 : 52,
            position_y: sequence % 2 ? 8 : 64,
            width: 40,
            height: 20,
          }),
        }),
      'Novo balão adicionado ao quadro.',
    )
  }

  async function removeBalloon() {
    if (!selectedBalloon) return
    setBusy(true)
    try {
      await api<void>(`/comics/${comicId}/balloons/${selectedBalloon.id}`, { method: 'DELETE' })
      setSuccess('Balão removido e versão registrada.')
      setSelectedBalloonId('')
      await load(selectedPanelId)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao remover balão.')
    } finally {
      setBusy(false)
    }
  }

  async function movePanel(direction: -1 | 1) {
    if (!selectedPage || !selectedPanel) return
    const ordered = [...selectedPage.panels].sort((a, b) => a.reading_order - b.reading_order)
    const index = ordered.findIndex((panel) => panel.id === selectedPanel.id)
    const target = index + direction
    if (index < 0 || target < 0 || target >= ordered.length) return
    ;[ordered[index], ordered[target]] = [ordered[target], ordered[index]]
    await perform(
      () =>
        api<Comic>(`/comics/${comicId}/pages/${selectedPage.id}/reorder`, {
          method: 'POST',
          body: JSON.stringify({ panel_ids: ordered.map((panel) => panel.id) }),
        }),
      'Ordem de leitura atualizada e versionada.',
    )
  }

  async function duplicatePanel() {
    if (!selectedPanel) return
    await perform(
      () => api<Comic>(`/comics/${comicId}/panels/${selectedPanel.id}/duplicate`, { method: 'POST' }),
      'Quadro duplicado para adaptação.',
    )
  }

  async function removePanel() {
    if (!selectedPanel) return
    setBusy(true)
    try {
      await api<void>(`/comics/${comicId}/panels/${selectedPanel.id}`, { method: 'DELETE' })
      setSuccess('Quadro removido. A ordem de leitura foi recalculada.')
      setSelectedPanelId('')
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao remover quadro.')
    } finally {
      setBusy(false)
    }
  }

  async function previewPolicy() {
    if (!selectedPage || !selectedPanel) return
    try {
      const policy = await api<RegenerationPolicy>(`/comics/${comicId}/regeneration-policy`, {
        method: 'POST',
        body: JSON.stringify({
          scope: regenScope,
          page_id: regenScope === 'page' ? selectedPage.id : null,
          panel_id: ['panel', 'balloons', 'dialogue', 'scene', 'from_panel'].includes(regenScope) ? selectedPanel.id : null,
          preserve_dialogue: preserveDialogue,
          preserve_scene: preserveScene,
          change_instruction: regenInstruction || null,
        }),
      })
      setRegenPolicy(policy)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao analisar o impacto da regeneração.')
    }
  }

  async function regenerate() {
    if (!selectedPage || !selectedPanel) return
    await perform(
      () =>
        api<Comic>(`/comics/${comicId}/regenerate`, {
          method: 'POST',
          body: JSON.stringify({
            scope: regenScope,
            page_id: regenScope === 'page' ? selectedPage.id : null,
            panel_id: ['panel', 'balloons', 'dialogue', 'scene', 'from_panel'].includes(regenScope)
              ? selectedPanel.id
              : null,
            preserve_dialogue: preserveDialogue,
            preserve_scene: preserveScene,
            change_instruction: regenInstruction || null,
          }),
        }),
      `Regeneração “${regenScope}” concluída sem sobrescrever o histórico.`,
    )
  }

  async function proposeAlternatives() {
    if (!selectedPanel) return
    setBusy(true)
    setError('')
    try {
      const result = await api<ComicRegenerationProposal[]>(`/comics/${comicId}/regeneration-proposals`, {
        method: 'POST',
        body: JSON.stringify({
          scope: regenScope === 'page' || regenScope === 'comic' ? 'panel' : regenScope,
          panel_id: selectedPanel.id,
          preserve_dialogue: preserveDialogue,
          preserve_scene: preserveScene,
          change_instruction: regenInstruction || null,
          alternative_count: 3,
          tones: ['funny', 'emotional', 'mysterious'],
        }),
      })
      setProposals(result)
      setSuccess('Três alternativas foram preparadas sem alterar a versão atual.')
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao gerar alternativas.')
    } finally {
      setBusy(false)
    }
  }

  async function acceptProposal(proposalId: string) {
    await perform(
      () => api<Comic>(`/comics/${comicId}/regeneration-proposals/${proposalId}/accept`, { method: 'POST' }),
      'Alternativa aceita como nova versão.',
    )
    setProposals([])
  }

  async function saveLocks(locks: string[]) {
    if (!selectedPanel) return
    await perform(
      () => api<Comic>(`/comics/${comicId}/panels/${selectedPanel.id}/locks`, {
        method: 'POST',
        body: JSON.stringify({ locked_elements: locks }),
      }),
      'Bloqueios do quadro atualizados.',
    )
  }

  async function addReviewComment() {
    if (!commentText.trim()) return
    setBusy(true)
    try {
      await api(`/comics/${comicId}/comments`, {
        method: 'POST',
        body: JSON.stringify({
          specialty: commentSpecialty,
          body: commentText,
          page_id: selectedPage?.id ?? null,
          panel_id: selectedPanel?.id ?? null,
          balloon_id: selectedBalloon?.id ?? null,
        }),
      })
      setCommentText('')
      setSuccess('Comentário de revisão registrado no elemento selecionado.')
      await load(selectedPanelId, selectedBalloonId)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao registrar comentário.')
    } finally {
      setBusy(false)
    }
  }

  async function setReviewDecision(specialty: ReviewSpecialty, decision: 'approved' | 'changes_requested') {
    setBusy(true)
    try {
      await api(`/comics/${comicId}/review-approvals`, {
        method: 'POST',
        body: JSON.stringify({ specialty, decision }),
      })
      setSuccess(`Revisão ${specialty} atualizada.`)
      await load(selectedPanelId, selectedBalloonId)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha na aprovação por especialidade.')
    } finally {
      setBusy(false)
    }
  }

  async function undoRedo(action: 'undo' | 'redo') {
    await perform(
      () => api<Comic>(`/comics/${comicId}/${action}`, { method: 'POST' }),
      action === 'undo' ? 'Última edição desfeita.' : 'Última edição refeita.',
    )
  }

  async function restoreVersion(versionId: string) {
    await perform(
      () =>
        api<Comic>(`/comics/${comicId}/versions/${versionId}/restore`, {
          method: 'POST',
          body: JSON.stringify({ change_description: 'Restauração solicitada no editor' }),
        }),
      'Versão restaurada como uma nova versão, sem apagar o histórico.',
    )
  }

  async function approve() {
    await perform(
      () => api<Comic>(`/comics/${comicId}/approve`, { method: 'POST' }),
      'HQ aprovada após a validação de continuidade.',
    )
  }

  async function saveGeneratedCharacter() {
    if (!characterName.trim()) {
      setError('Informe um nome para salvar o personagem.')
      return
    }
    setBusy(true)
    setError('')
    try {
      await api(`/comics/${comicId}/characters/save`, {
        method: 'POST',
        body: JSON.stringify({
          name: characterName.trim(),
          page_id: selectedPage?.id ?? null,
          panel_id: selectedPanel?.id ?? null,
          description: selectedPanel?.scene_description ?? null,
          personality: selectedPanel?.emotion ?? null,
          canonical_prompt: JSON.stringify(selectedPanel?.visual_prompt ?? {}),
          immutable_traits: [],
          destination: characterDestination,
          rights_confirmed: true,
        }),
      })
      setSuccess(characterDestination === 'institutional_review'
        ? `Personagem “${characterName}” enviado para aprovação institucional.`
        : `Personagem “${characterName}” salvo na biblioteca.`)
      setCharacterName('')
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao salvar o personagem.')
    } finally {
      setBusy(false)
    }
  }

  async function exportStructured(kind: 'json' | 'canvas') {
    try {
      const data = await api<Record<string, unknown>>(`/comics/${comicId}/export/${kind}`)
      downloadJson(`${comic?.title ?? 'hq'}-${kind}.json`, data)
      setSuccess(kind === 'canvas' ? 'Pacote para canvas exportado.' : 'JSON estruturado exportado.')
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha na exportação.')
    }
  }

  if (!comic || !selectedPage) {
    return <section className="page-stack"><p>Carregando editor de HQ…</p></section>
  }

  return (
    <section className="page-stack comic-editor-page">
      <header className="page-header comic-editor-header">
        <div>
          <span className="eyebrow">ESTABILIZAÇÃO E PRONTIDÃO · SPRINT 07.2</span>
          <h1>{comic.title}</h1>
          <p>{comic.synopsis}</p>
          <div className="score-grid">
            <span>Versão <strong>v{comic.current_version}</strong></span>
            <span>Continuidade <strong>{percentage(comic.continuity_score)}</strong></span>
            <span>Pedagogia <strong>{percentage(comic.pedagogical_score)}</strong></span>
            <span>Status <strong>{comic.status}</strong></span>
            <span>Autosave <strong>{comic.last_saved_at ? new Date(comic.last_saved_at).toLocaleTimeString('pt-BR') : 'pendente'}</strong></span>
            <span>Revisão de edição <strong>{comic.edit_revision}</strong></span>
            <span>Última edição <strong>{comic.last_editor_name_snapshot ?? comic.created_by_name_snapshot}</strong></span>
            <span>Canvas <strong>{readiness?.status ?? comic.canvas_readiness_status}</strong></span>
          </div>
        </div>
        <div className="comic-header-actions">
          <Link className="secondary-button" to="/hqs">Voltar às HQs</Link>
          <button type="button" onClick={() => void undoRedo('undo')}>Desfazer</button>
          <button type="button" onClick={() => void undoRedo('redo')}>Refazer</button>
          <button type="button" onClick={() => void exportStructured('json')}>Exportar JSON</button>
          <button type="button" onClick={() => void exportStructured('canvas')}>Pacote para canvas</button>
          <button className="primary" type="button" onClick={() => void approve()} disabled={busy || comic.status === 'approved'}>Aprovar HQ</button>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}
      <div className="panel">
        <div className="section-heading">
          <div><span className="eyebrow">PERSONAGEM DA HQ</span><h2>Salvar personagem com nome</h2><p>Reutilize o personagem em novos projetos ou envie-o para aprovação institucional.</p></div>
        </div>
        <div className="toolbar">
          <input value={characterName} onChange={(event) => setCharacterName(event.target.value)} placeholder="Nome do personagem" />
          <select value={characterDestination} onChange={(event) => setCharacterDestination(event.target.value as 'project' | 'personal' | 'institutional_review')}>
            <option value="project">Biblioteca do projeto</option>
            <option value="personal">Minha biblioteca</option>
            <option value="institutional_review">Enviar para aprovação institucional</option>
          </select>
          <button type="button" onClick={() => void saveGeneratedCharacter()} disabled={busy || !selectedPanel}>Salvar personagem</button>
        </div>
      </div>
      {localDraftAvailable ? (
        <div className="alert">
          <strong>Rascunho local recuperável</strong>
          <span>{localDraftSavedAt ? ` salvo em ${new Date(localDraftSavedAt).toLocaleString('pt-BR')}` : ''}</span>
          <div className="card-actions">
            <button type="button" onClick={restoreLocalDraft}>Restaurar campos visíveis</button>
            <button type="button" onClick={discardLocalDraft}>Descartar rascunho</button>
          </div>
        </div>
      ) : null}

      <div className="editor-mode-switch" role="group" aria-label="Modo de edição">
        <button className={mode === 'teacher' ? 'active' : ''} type="button" onClick={() => setMode('teacher')}>Modo professor</button>
        <button className={mode === 'designer' ? 'active' : ''} type="button" onClick={() => setMode('designer')}>Modo designer</button>
      </div>

      <div className="comic-editor-grid">
        <aside className="comic-page-list panel">
          <span className="eyebrow">PÁGINAS</span>
          {comic.pages.map((page) => (
            <button key={page.id} type="button" className={page.id === selectedPage.id ? 'active' : ''} onClick={() => choosePage(page)}>
              <strong>Página {page.page_number}</strong>
              <small>{page.panel_count} quadros · {page.layout_template}</small>
            </button>
          ))}
          <div className="continuity-mini-card">
            <strong>Validação</strong>
            <span>{continuity?.issue_count ?? 0} observações</span>
            <small>{continuity?.is_valid ? 'Sem erros bloqueantes' : 'Revisão necessária'}</small>
          </div>
        </aside>

        <main className="comic-canvas-workspace panel">
          <div className="panel-title-row">
            <div>
              <span className="eyebrow">PRÉVIA ESTRUTURAL</span>
              <h2>Página {selectedPage.page_number}</h2>
            </div>
            <span>{selectedPage.orientation === 'portrait' ? 'A4 vertical' : 'A4 horizontal'}</span>
          </div>
          <div className={`comic-page-preview ${selectedPage.orientation}`}>
            {selectedPage.panels.map((panel) => (
              <button
                key={panel.id}
                type="button"
                className={`comic-panel-preview shape-${panel.shape} ${panel.id === selectedPanel?.id ? 'selected' : ''}`}
                style={{
                  left: `${panel.position_x}%`,
                  top: `${panel.position_y}%`,
                  width: `${panel.width}%`,
                  height: `${panel.height}%`,
                  transform: `rotate(${panel.rotation}deg)`,
                  zIndex: panel.z_index,
                }}
                onClick={() => choosePanel(panel)}
              >
                <span className="panel-index">{panel.reading_order}{panel.locked_elements.length ? ' 🔒' : ''}</span>
                <strong>{panel.plot_function}</strong>
                <small>{panel.emotion}</small>
                <p>{panel.scene_description}</p>
                <div className="preview-balloons">
                  {panel.balloons.slice(0, 3).map((balloon) => (
                    <span key={balloon.id}>{balloon.speaker_name_snapshot ? `${balloon.speaker_name_snapshot}: ` : ''}{balloon.text}</span>
                  ))}
                </div>
              </button>
            ))}
          </div>
          <div className="comic-panel-strip">
            {selectedPage.panels.map((panel) => (
              <button key={panel.id} type="button" className={panel.id === selectedPanel?.id ? 'active' : ''} onClick={() => choosePanel(panel)}>
                Q{panel.reading_order} · {shapeLabels[panel.shape]}
              </button>
            ))}
          </div>
        </main>

        <aside className="comic-properties panel">
          {mode === 'teacher' ? (
            <TeacherProperties
              panel={selectedPanel}
              balloon={selectedBalloon}
              busy={busy}
              onSavePanel={savePanel}
              onSaveBalloon={saveBalloon}
              onChooseBalloon={setSelectedBalloonId}
              onAddBalloon={addBalloon}
              onRemoveBalloon={removeBalloon}
            />
          ) : (
            <DesignerProperties
              page={selectedPage}
              panel={selectedPanel}
              templates={templates}
              busy={busy}
              onSavePage={savePage}
              onSavePanel={savePanel}
            />
          )}
        </aside>
      </div>

      <section className="panel regeneration-panel">
        <div>
          <span className="eyebrow">REGENERAÇÃO PARCIAL</span>
          <h2>Corrija somente o necessário</h2>
          <p>O sistema registra uma nova versão e preserva as páginas e quadros que não foram selecionados.</p>
        </div>
        <div className="form-grid studio-three-columns">
          <label>
            Escopo
            <select value={regenScope} onChange={(event) => setRegenScope(event.target.value as GenerationScope)}>
              <option value="panel">Quadro específico</option>
              <option value="balloons">Somente balões</option>
              <option value="dialogue">Somente diálogos</option>
              <option value="scene">Somente descrição da cena</option>
              <option value="page">Página atual</option>
              <option value="from_panel">Quadro atual e seguintes</option>
              <option value="comic">HQ inteira</option>
            </select>
          </label>
          <label className="full-width">
            Orientação da correção
            <textarea rows={3} value={regenInstruction} onChange={(event) => setRegenInstruction(event.target.value)} placeholder="Ex.: deixar mais engraçado, corrigir a explicação e manter a pista para o plot twist." />
          </label>
          <label className="checkbox-line">
            <input type="checkbox" checked={preserveDialogue} onChange={(event) => setPreserveDialogue(event.target.checked)} />
            Manter diálogos
          </label>
          <label className="checkbox-line">
            <input type="checkbox" checked={preserveScene} onChange={(event) => setPreserveScene(event.target.checked)} />
            Manter descrição visual
          </label>
        </div>
        <div className="card-actions">
          <button type="button" onClick={() => void movePanel(-1)} disabled={busy || !selectedPanel}>Mover antes</button>
          <button type="button" onClick={() => void movePanel(1)} disabled={busy || !selectedPanel}>Mover depois</button>
          <button type="button" onClick={() => void duplicatePanel()} disabled={busy || !selectedPanel}>Duplicar quadro</button>
          <button type="button" onClick={() => void removePanel()} disabled={busy || !selectedPanel}>Excluir quadro</button>
          <button type="button" onClick={() => void previewPolicy()} disabled={busy || !selectedPanel}>Ver impacto</button>
          <button type="button" onClick={() => void proposeAlternatives()} disabled={busy || !selectedPanel}>Comparar 3 alternativas</button>
          <button className="primary" type="button" onClick={() => void regenerate()} disabled={busy || !selectedPanel}>Regenerar diretamente</button>
        </div>
        {regenPolicy ? (
          <div className="subtle-card">
            <strong>Política da regeneração</strong>
            <p>{regenPolicy.affected_panel_ids.length} quadro(s) poderão ser afetados.</p>
            <small>Mutável: {regenPolicy.mutable_elements.join(', ') || 'nenhum elemento desbloqueado'}</small>
            {regenPolicy.warnings.map((warning) => <div className="alert" key={warning}>{warning}</div>)}
          </div>
        ) : null}
      </section>

      <section className="panel">
        <span className="eyebrow">BLOQUEIOS E ALTERNATIVAS</span>
        <h2>Preserve o que já está correto</h2>
        <div className="lock-grid">
          {['panel', 'dialogue', 'balloons', 'scene', 'layout', 'pedagogical_goal', 'visual_prompt'].map((lock) => (
            <label className="checkbox-line" key={lock}>
              <input
                type="checkbox"
                checked={selectedPanel?.locked_elements.includes(lock) ?? false}
                onChange={(event) => {
                  const current = new Set(selectedPanel?.locked_elements ?? [])
                  if (event.target.checked) current.add(lock); else current.delete(lock)
                  void saveLocks([...current])
                }}
              />
              {lock}
            </label>
          ))}
        </div>
        {proposals.length ? (
          <div className="proposal-grid">
            {proposals.map((proposal) => {
              const payload = proposal.proposal_payload
              const balloons = Array.isArray(payload.balloons) ? payload.balloons : []
              return (
                <article key={proposal.id} className="subtle-card">
                  <strong>{proposal.label}</strong>
                  <small>{proposal.tone}</small>
                  <p>{String(payload.scene_description ?? '')}</p>
                  {balloons.slice(0, 2).map((item, index) => (
                    <blockquote key={index}>{String((item as Record<string, unknown>).text ?? '')}</blockquote>
                  ))}
                  <button className="primary" type="button" onClick={() => void acceptProposal(proposal.id)}>Aceitar alternativa</button>
                </article>
              )
            })}
          </div>
        ) : <p>Gere alternativas para comparar sem substituir o quadro atual.</p>}
      </section>

      <section className="panel">
        <span className="eyebrow">MAPA NARRATIVO</span>
        <h2>Ritmo, pistas e carga de texto</h2>
        {narrativeMap?.pacing_warnings.map((warning) => <div className="alert" key={warning}>{warning}</div>)}
        <div className="narrative-map-grid">
          {narrativeMap?.items.map((item) => (
            <button key={item.panel_id} type="button" className={item.over_text_limit ? 'subtle-card warning-card' : 'subtle-card'} onClick={() => setSelectedPanelId(item.panel_id)}>
              <strong>P{item.page_number} · Q{item.reading_order}</strong>
              <span>{item.plot_function} · {item.pacing}</span>
              <small>{item.word_count} palavras{item.over_text_limit ? ' · acima do limite' : ''}</small>
            </button>
          ))}
        </div>
      </section>

      <section className="panel">
        <span className="eyebrow">ESTABILIDADE E PRONTIDÃO PARA O CANVAS</span>
        <h2>Linguagem, densidade, balões e checklist técnico</h2>
        <div className="score-grid">
          <span>Estabilidade <strong>{percentage(stability?.score ?? 0)}</strong></span>
          <span>Palavras <strong>{stability?.language_metrics.word_count ?? 0}</strong></span>
          <span>Média por frase <strong>{stability?.language_metrics.average_words_per_sentence ?? 0}</strong></span>
          <span>Status canvas <strong>{readiness?.status ?? 'não verificado'}</strong></span>
        </div>
        <div className="proposal-grid">
          {readiness?.checklist.map((item) => (
            <article key={item.code} className="subtle-card">
              <strong>{item.passed ? '✓' : item.required ? '✕' : '!' } {item.label}</strong>
              <small>{item.required ? 'Obrigatório' : 'Recomendado'}</small>
            </article>
          ))}
        </div>
        {stability?.page_densities.map((page) => (
          <p key={page.page_id}>Página {page.page_number}: densidade {page.classification} · {page.word_count} palavras · {percentage(page.density_score)}</p>
        ))}
        {stability?.findings.slice(0, 12).map((finding, index) => (
          <div className={`alert ${finding.severity === 'error' ? 'error' : ''}`} key={`${finding.code}-${index}`}>{finding.message}</div>
        ))}
      </section>

      <section className="panel review-workflow">
        <span className="eyebrow">REVISÃO POR ESPECIALIDADE</span>
        <h2>Comentários e aprovações independentes</h2>
        <div className="form-grid studio-three-columns">
          <label>Especialidade<select value={commentSpecialty} onChange={(event) => setCommentSpecialty(event.target.value as ReviewSpecialty)}><option value="narrative">Narrativa</option><option value="pedagogical">Pedagógica</option><option value="visual">Visual</option><option value="accessibility">Acessibilidade</option></select></label>
          <label className="full-width">Comentário<textarea rows={3} value={commentText} onChange={(event) => setCommentText(event.target.value)} placeholder="Ex.: a fala revela a solução cedo demais." /></label>
          <button type="button" onClick={() => void addReviewComment()} disabled={busy}>Adicionar comentário</button>
        </div>
        <div className="review-decision-grid">
          {(['narrative', 'pedagogical', 'visual', 'accessibility'] as ReviewSpecialty[]).map((specialty) => (
            <div className="subtle-card" key={specialty}>
              <strong>{specialty}</strong>
              <span>{String(comic.review_state[specialty] ?? 'pending')}</span>
              <div className="card-actions">
                <button type="button" onClick={() => void setReviewDecision(specialty, 'approved')}>Aprovar</button>
                <button type="button" onClick={() => void setReviewDecision(specialty, 'changes_requested')}>Solicitar ajustes</button>
              </div>
            </div>
          ))}
        </div>
        <div className="version-timeline">
          {comic.review_comments.slice(0, 6).map((comment) => (
            <div key={comment.id}><strong>{comment.specialty}</strong><span>{comment.body}</span><small>{comment.author_name_snapshot} · {comment.status}</small></div>
          ))}
        </div>
      </section>

      <section className="panel">
        <span className="eyebrow">HISTÓRICO</span>
        <h2>Versões recentes</h2>
        <div className="version-timeline">
          {comic.versions.slice(0, 8).map((version) => (
            <div key={version.id}>
              <strong>v{version.version_number}</strong>
              <span>{version.change_description}</span>
              <small>{new Date(version.created_at).toLocaleString('pt-BR')}</small>
              <button type="button" onClick={() => void restoreVersion(version.id)} disabled={busy}>Restaurar</button>
            </div>
          ))}
        </div>
      </section>
    </section>
  )
}

interface TeacherPropertiesProps {
  panel: ComicPanel | null
  balloon: ComicBalloon | null
  busy: boolean
  onSavePanel: (event: FormEvent<HTMLFormElement>) => Promise<void>
  onSaveBalloon: (event: FormEvent<HTMLFormElement>) => Promise<void>
  onChooseBalloon: (id: string) => void
  onAddBalloon: () => Promise<void>
  onRemoveBalloon: () => Promise<void>
}

function TeacherProperties(props: TeacherPropertiesProps) {
  const { panel, balloon } = props
  if (!panel) return <p>Selecione um quadro.</p>
  return (
    <div className="properties-stack">
      <span className="eyebrow">MODO PROFESSOR</span>
      <h2>Conteúdo do quadro {panel.reading_order}</h2>
      <form key={`teacher-panel-${panel.id}-${panel.updated_at}`} className="compact-form" data-draft-scope={`teacher-panel-${panel.id}`} onSubmit={props.onSavePanel}>
        <label>Objetivo narrativo<textarea name="narrative_goal" rows={3} defaultValue={panel.narrative_goal} /></label>
        <label>Objetivo pedagógico<textarea name="pedagogical_goal" rows={3} defaultValue={panel.pedagogical_goal} /></label>
        <label>Resumo do quadro anterior<textarea name="previous_panel_summary" rows={2} defaultValue={panel.previous_panel_summary} /></label>
        <label>Descrição da cena<textarea name="scene_description" rows={4} defaultValue={panel.scene_description} /></label>
        <label>Gancho para o próximo<textarea name="next_panel_hook" rows={2} defaultValue={panel.next_panel_hook} /></label>
        <div className="form-grid two-columns">
          <label>Emoção<input name="emotion" defaultValue={panel.emotion} /></label>
          <label>Função no enredo<input name="plot_function" defaultValue={panel.plot_function} /></label>
          <label>Ritmo<select name="pacing" defaultValue={panel.pacing}><option value="pause">Pausa</option><option value="slow">Lento</option><option value="moderate">Moderado</option><option value="fast">Rápido</option><option value="impactful">Impactante</option><option value="revelation">Revelação</option></select></label>
          <label>Limite de palavras<input type="number" name="text_word_limit" min={10} max={500} defaultValue={panel.text_word_limit} /></label>
        </div>
        <label>Texto alternativo<textarea name="alt_text" rows={2} defaultValue={panel.alt_text ?? ''} /></label>
        <label>Audiodescrição<textarea name="audio_description" rows={3} defaultValue={panel.audio_description ?? ''} /></label>
        <label>Prompt visual estruturado<textarea name="visual_prompt_json" rows={7} defaultValue={JSON.stringify(panel.visual_prompt, null, 2)} /></label>
        <input type="hidden" name="shape" value={panel.shape} />
        <input type="hidden" name="size_category" value={panel.size_category} />
        <input type="hidden" name="position_x" value={panel.position_x} />
        <input type="hidden" name="position_y" value={panel.position_y} />
        <input type="hidden" name="width" value={panel.width} />
        <input type="hidden" name="height" value={panel.height} />
        <input type="hidden" name="rotation" value={panel.rotation} />
        <button className="primary" type="submit" disabled={props.busy}>Salvar conteúdo do quadro</button>
      </form>

      <div className="balloon-editor-list">
        <div className="panel-title-row">
          <h3>Balões e falas</h3>
          <button type="button" onClick={() => void props.onAddBalloon()}>Adicionar</button>
        </div>
        <div className="comic-panel-strip">
          {panel.balloons.map((item) => (
            <button key={item.id} type="button" className={item.id === balloon?.id ? 'active' : ''} onClick={() => props.onChooseBalloon(item.id)}>
              {item.sequence_number}. {item.speaker_name_snapshot ?? balloonLabels[item.balloon_type]}
            </button>
          ))}
        </div>
        {balloon ? (
          <form key={`balloon-${balloon.id}-${balloon.updated_at}`} className="compact-form" data-draft-scope={`balloon-${balloon.id}`} onSubmit={props.onSaveBalloon}>
            <label>Personagem<input name="speaker_name_snapshot" defaultValue={balloon.speaker_name_snapshot ?? ''} /></label>
            <label>Tipo<select name="balloon_type" defaultValue={balloon.balloon_type}>{Object.entries(balloonLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label>Texto<textarea required name="text" rows={4} defaultValue={balloon.text} /></label>
            <label>Emoção<input name="emotion" defaultValue={balloon.emotion ?? ''} /></label>
            <label>Função pedagógica<input name="pedagogical_function" defaultValue={balloon.pedagogical_function ?? ''} /></label>
            <label className="checkbox-line"><input type="checkbox" name="is_locked" defaultChecked={balloon.is_locked} />Bloquear este balão</label>
            <div className="form-grid two-columns">
              <label>X<input type="number" step="0.1" name="position_x" defaultValue={balloon.position_x} /></label>
              <label>Y<input type="number" step="0.1" name="position_y" defaultValue={balloon.position_y} /></label>
              <label>Largura<input type="number" step="0.1" name="width" defaultValue={balloon.width} /></label>
              <label>Altura<input type="number" step="0.1" name="height" defaultValue={balloon.height} /></label>
            </div>
            <div className="card-actions">
              <button className="primary" type="submit" disabled={props.busy}>Salvar balão</button>
              <button type="button" onClick={() => void props.onRemoveBalloon()} disabled={props.busy}>Excluir balão</button>
            </div>
          </form>
        ) : <p>Adicione ou selecione um balão.</p>}
      </div>
    </div>
  )
}

interface DesignerPropertiesProps {
  page: ComicPage
  panel: ComicPanel | null
  templates: LayoutTemplate[]
  busy: boolean
  onSavePage: (event: FormEvent<HTMLFormElement>) => Promise<void>
  onSavePanel: (event: FormEvent<HTMLFormElement>) => Promise<void>
}

function DesignerProperties(props: DesignerPropertiesProps) {
  const { page, panel } = props
  return (
    <div className="properties-stack">
      <span className="eyebrow">MODO DESIGNER</span>
      <h2>Composição da página</h2>
      <form key={`page-${page.id}-${page.updated_at}`} className="compact-form" data-draft-scope={`page-${page.id}`} onSubmit={props.onSavePage}>
        <label>Quantidade de quadros<input type="number" min={1} max={8} name="panel_count" defaultValue={page.panel_count} /></label>
        <label>Modelo de layout<select name="layout_template" defaultValue={page.layout_template}>{props.templates.map((template) => <option key={template.code} value={template.code}>{template.label} · {template.panel_count}</option>)}</select></label>
        <label>Formato<select name="page_format" defaultValue={page.page_format}><option value="a4">A4</option><option value="square">Quadrado</option><option value="mobile">Celular</option><option value="instagram">Instagram</option><option value="presentation_16_9">Apresentação 16:9</option><option value="custom">Personalizado</option></select></label>
        <label>Orientação<select name="orientation" defaultValue={page.orientation}><option value="portrait">Vertical</option><option value="landscape">Horizontal</option></select></label>
        <label>Ordem de leitura<select name="reading_direction" defaultValue={page.reading_direction}><option value="left_to_right">Esquerda para direita</option><option value="right_to_left">Direita para esquerda</option><option value="top_to_bottom">Cima para baixo</option></select></label>
        <label>Observações<textarea name="notes" rows={2} defaultValue={page.notes ?? ''} /></label>
        <button className="primary" type="submit" disabled={props.busy}>Aplicar composição</button>
      </form>

      {panel ? (
        <form key={`designer-panel-${panel.id}-${panel.updated_at}`} className="compact-form" data-draft-scope={`designer-panel-${panel.id}`} onSubmit={props.onSavePanel}>
          <h3>Formato do quadro {panel.reading_order}</h3>
          <label>Forma<select name="shape" defaultValue={panel.shape}>{Object.entries(shapeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <label>Tamanho<select name="size_category" defaultValue={panel.size_category}>{Object.entries(sizeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <div className="form-grid two-columns">
            <label>X<input type="number" step="0.1" name="position_x" defaultValue={panel.position_x} /></label>
            <label>Y<input type="number" step="0.1" name="position_y" defaultValue={panel.position_y} /></label>
            <label>Largura<input type="number" step="0.1" name="width" defaultValue={panel.width} /></label>
            <label>Altura<input type="number" step="0.1" name="height" defaultValue={panel.height} /></label>
            <label>Rotação<input type="number" step="0.5" name="rotation" defaultValue={panel.rotation} /></label>
          </div>
          <input type="hidden" name="narrative_goal" value={panel.narrative_goal} />
          <input type="hidden" name="pedagogical_goal" value={panel.pedagogical_goal} />
          <input type="hidden" name="scene_description" value={panel.scene_description} />
          <input type="hidden" name="previous_panel_summary" value={panel.previous_panel_summary} />
          <input type="hidden" name="next_panel_hook" value={panel.next_panel_hook} />
          <input type="hidden" name="emotion" value={panel.emotion} />
          <input type="hidden" name="plot_function" value={panel.plot_function} />
          <input type="hidden" name="pacing" value={panel.pacing} />
          <input type="hidden" name="text_word_limit" value={panel.text_word_limit} />
          <input type="hidden" name="alt_text" value={panel.alt_text ?? ''} />
          <input type="hidden" name="audio_description" value={panel.audio_description ?? ''} />
          <input type="hidden" name="visual_prompt_json" value={JSON.stringify(panel.visual_prompt)} />
          <button className="primary" type="submit" disabled={props.busy}>Salvar formato do quadro</button>
        </form>
      ) : null}
    </div>
  )
}
