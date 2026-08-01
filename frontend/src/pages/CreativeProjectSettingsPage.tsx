import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import type {
  CreativeBible,
  CreativeItem,
  CreativeItemKind,
  CreativeProjectLink,
} from '../types/creative'
import type { GenerationProject } from '../types/pedagogy'

const kindLabels: Record<CreativeItemKind, string> = {
  character: 'Personagens',
  scene: 'Cenários',
  style: 'Estilos',
}

interface BibleForm {
  title: string
  ageGroup: string
  visualLanguage: string
  narrativeTone: string
  pedagogicalTone: string
  colorPalette: string
  mandatoryRules: string
  prohibitedElements: string
  institutionName: string
  footer: string
  notes: string
}

const emptyBible: BibleForm = {
  title: '',
  ageGroup: '',
  visualLanguage: '',
  narrativeTone: '',
  pedagogicalTone: '',
  colorPalette: '',
  mandatoryRules: '',
  prohibitedElements: '',
  institutionName: '',
  footer: '',
  notes: '',
}

function lines(value: string) {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

export function CreativeProjectSettingsPage() {
  const { generationProjectId } = useParams()
  const { user } = useAuth()
  const role = user?.memberships[0]?.role
  const canWrite = ['owner', 'admin', 'teacher'].includes(role ?? '')

  const [project, setProject] = useState<GenerationProject | null>(null)
  const [items, setItems] = useState<CreativeItem[]>([])
  const [links, setLinks] = useState<CreativeProjectLink[]>([])
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [roles, setRoles] = useState<Record<string, string>>({})
  const [primaryIds, setPrimaryIds] = useState<string[]>([])
  const [bible, setBible] = useState<BibleForm>(emptyBible)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [busy, setBusy] = useState(false)

  async function loadData() {
    if (!generationProjectId) return
    setError('')
    try {
      const [projectData, itemData, linkData, bibleData] = await Promise.all([
        api<GenerationProject>(`/generation-projects/${generationProjectId}`),
        api<CreativeItem[]>('/creative/items?status=active'),
        api<CreativeProjectLink[]>(`/creative/generation-projects/${generationProjectId}/items`),
        api<CreativeBible | null>(`/creative/generation-projects/${generationProjectId}/bible`),
      ])
      setProject(projectData)
      setItems(itemData)
      setLinks(linkData)
      setSelectedIds(linkData.map((link) => link.creative_item_id))
      setPrimaryIds(linkData.filter((link) => link.is_primary).map((link) => link.creative_item_id))
      setRoles(
        Object.fromEntries(
          linkData.map((link) => [link.creative_item_id, link.narrative_role ?? '']),
        ),
      )
      setBible(
        bibleData
          ? {
              title: bibleData.title,
              ageGroup: bibleData.age_group ?? '',
              visualLanguage: bibleData.visual_language ?? '',
              narrativeTone: bibleData.narrative_tone ?? '',
              pedagogicalTone: bibleData.pedagogical_tone ?? '',
              colorPalette: bibleData.color_palette.join('\n'),
              mandatoryRules: bibleData.mandatory_rules.join('\n'),
              prohibitedElements: bibleData.prohibited_elements.join('\n'),
              institutionName: String(bibleData.institution_identity.name ?? ''),
              footer: String(bibleData.institution_identity.footer ?? ''),
              notes: bibleData.notes ?? '',
            }
          : { ...emptyBible, title: `Bíblia Criativa — ${projectData.title}` },
      )
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível carregar o universo criativo.',
      )
    }
  }

  useEffect(() => {
    void loadData()
  }, [generationProjectId])

  const grouped = useMemo(
    () =>
      (['character', 'scene', 'style'] as const).map((kind) => ({
        kind,
        items: items.filter((item) => item.kind === kind),
      })),
    [items],
  )

  function toggleItem(itemId: string) {
    setSelectedIds((current) =>
      current.includes(itemId)
        ? current.filter((id) => id !== itemId)
        : [...current, itemId],
    )
  }

  function togglePrimary(itemId: string) {
    setPrimaryIds((current) =>
      current.includes(itemId)
        ? current.filter((id) => id !== itemId)
        : [...current, itemId],
    )
  }

  async function saveLinks() {
    if (!generationProjectId) return
    setBusy(true)
    setError('')
    setSuccess('')
    try {
      await api<CreativeProjectLink[]>(
        `/creative/generation-projects/${generationProjectId}/items`,
        {
          method: 'PUT',
          body: JSON.stringify(
            selectedIds.map((creativeItemId, index) => ({
              creative_item_id: creativeItemId,
              creative_version_id: null,
              narrative_role: roles[creativeItemId]?.trim() || null,
              position: index,
              is_primary: primaryIds.includes(creativeItemId),
            })),
          ),
        },
      )
      setSuccess('Personagens, cenários e estilos vinculados ao projeto.')
      await loadData()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao salvar vínculos.')
    } finally {
      setBusy(false)
    }
  }

  async function saveBible(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!generationProjectId) return
    setBusy(true)
    setError('')
    setSuccess('')
    try {
      await api<CreativeBible>(
        `/creative/generation-projects/${generationProjectId}/bible`,
        {
          method: 'PUT',
          body: JSON.stringify({
            title: bible.title.trim(),
            age_group: bible.ageGroup.trim() || null,
            visual_language: bible.visualLanguage.trim() || null,
            narrative_tone: bible.narrativeTone.trim() || null,
            pedagogical_tone: bible.pedagogicalTone.trim() || null,
            color_palette: lines(bible.colorPalette),
            mandatory_rules: lines(bible.mandatoryRules),
            prohibited_elements: lines(bible.prohibitedElements),
            institution_identity: {
              name: bible.institutionName.trim(),
              footer: bible.footer.trim(),
            },
            notes: bible.notes.trim() || null,
          }),
        },
      )
      setSuccess('Bíblia Criativa salva.')
      await loadData()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao salvar a Bíblia Criativa.')
    } finally {
      setBusy(false)
    }
  }

  if (!generationProjectId) return <p>Projeto inválido.</p>

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <span className="eyebrow">UNIVERSO CRIATIVO DO PROJETO</span>
          <h1>{project?.title ?? 'Carregando...'}</h1>
          <p>Defina referências e regras que deverão permanecer em todos os materiais.</p>
        </div>
        <Link className="button-link" to="/estudio-pedagogico">Voltar ao estúdio</Link>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}

      <section className="panel">
        <div className="panel-title-row">
          <div>
            <h2>Pacote visual</h2>
            <p>Selecione personagens, cenários e estilos ativos na Biblioteca Criativa.</p>
          </div>
          <Link to="/biblioteca-criativa">Abrir biblioteca</Link>
        </div>
        {grouped.map((group) => (
          <fieldset className="studio-fieldset" key={group.kind}>
            <legend>{kindLabels[group.kind]}</legend>
            <div className="creative-selection-list">
              {group.items.map((item) => {
                const selected = selectedIds.includes(item.id)
                return (
                  <article className={selected ? 'creative-select-card selected' : 'creative-select-card'} key={item.id}>
                    <label className="checkbox-row">
                      <input checked={selected} onChange={() => toggleItem(item.id)} type="checkbox" />
                      <strong>{item.name}</strong>
                    </label>
                    <p>{item.description || 'Sem descrição.'}</p>
                    {selected ? (
                      <div className="form-grid studio-two-columns">
                        <label>
                          Papel no projeto
                          <input
                            placeholder={group.kind === 'character' ? 'Protagonista, mediador...' : 'Principal, apoio...'}
                            value={roles[item.id] ?? ''}
                            onChange={(event) => setRoles((current) => ({ ...current, [item.id]: event.target.value }))}
                          />
                        </label>
                        <label className="checkbox-row">
                          <input checked={primaryIds.includes(item.id)} onChange={() => togglePrimary(item.id)} type="checkbox" />
                          Referência principal
                        </label>
                      </div>
                    ) : null}
                  </article>
                )
              })}
              {group.items.length === 0 ? <p>Nenhum item ativo nesta categoria.</p> : null}
            </div>
          </fieldset>
        ))}
        {canWrite ? <button className="primary" disabled={busy} onClick={() => void saveLinks()} type="button">Salvar pacote visual</button> : null}
      </section>

      <form className="panel" onSubmit={saveBible}>
        <div className="panel-title-row">
          <div>
            <h2>Bíblia Criativa Pedagógica</h2>
            <p>Centraliza identidade visual, regras narrativas e cuidados pedagógicos.</p>
          </div>
        </div>
        <div className="form-grid studio-two-columns">
          <label>
            Título
            <input value={bible.title} onChange={(event) => setBible((current) => ({ ...current, title: event.target.value }))} required />
          </label>
          <label>
            Faixa etária
            <input value={bible.ageGroup} onChange={(event) => setBible((current) => ({ ...current, ageGroup: event.target.value }))} />
          </label>
          <label>
            Linguagem visual
            <textarea rows={4} value={bible.visualLanguage} onChange={(event) => setBible((current) => ({ ...current, visualLanguage: event.target.value }))} />
          </label>
          <label>
            Tom narrativo
            <textarea rows={4} value={bible.narrativeTone} onChange={(event) => setBible((current) => ({ ...current, narrativeTone: event.target.value }))} />
          </label>
          <label>
            Tom pedagógico
            <textarea rows={4} value={bible.pedagogicalTone} onChange={(event) => setBible((current) => ({ ...current, pedagogicalTone: event.target.value }))} />
          </label>
          <label>
            Paleta de cores
            <textarea rows={4} placeholder="Uma cor ou código por linha" value={bible.colorPalette} onChange={(event) => setBible((current) => ({ ...current, colorPalette: event.target.value }))} />
          </label>
          <label>
            Regras obrigatórias
            <textarea rows={6} placeholder="Uma regra por linha" value={bible.mandatoryRules} onChange={(event) => setBible((current) => ({ ...current, mandatoryRules: event.target.value }))} />
          </label>
          <label>
            Elementos proibidos
            <textarea rows={6} placeholder="Um item por linha" value={bible.prohibitedElements} onChange={(event) => setBible((current) => ({ ...current, prohibitedElements: event.target.value }))} />
          </label>
          <label>
            Instituição
            <input value={bible.institutionName} onChange={(event) => setBible((current) => ({ ...current, institutionName: event.target.value }))} />
          </label>
          <label>
            Rodapé institucional
            <input value={bible.footer} onChange={(event) => setBible((current) => ({ ...current, footer: event.target.value }))} />
          </label>
          <label className="full-width">
            Observações
            <textarea rows={5} value={bible.notes} onChange={(event) => setBible((current) => ({ ...current, notes: event.target.value }))} />
          </label>
        </div>
        {canWrite ? <button className="primary" disabled={busy} type="submit">Salvar Bíblia Criativa</button> : null}
      </form>

      {links.length > 0 ? (
        <section className="panel">
          <h2>Resumo dos vínculos atuais</h2>
          <div className="generation-meta">
            {links.map((link) => (
              <span key={link.id}>{kindLabels[link.kind]}: {link.name}{link.narrative_role ? ` — ${link.narrative_role}` : ''}</span>
            ))}
          </div>
        </section>
      ) : null}
    </section>
  )
}
