import { FormEvent, useEffect, useMemo, useState } from 'react'

import { useAuth } from '../contexts/AuthContext'
import { api, apiBlob } from '../lib/api'
import type {
  CreativeAsset,
  CreativeCatalog,
  CreativeItem,
  CreativeItemKind,
  CreativeStatus,
  CreativeVisibility,
} from '../types/creative'

const kindLabels: Record<CreativeItemKind, string> = {
  character: 'Personagens',
  scene: 'Cenários',
  style: 'Estilos',
}

const visibilityLabels: Record<CreativeVisibility, string> = {
  private: 'Privado',
  team: 'Equipe',
  organization: 'Organização',
}

const statusLabels: Record<CreativeStatus, string> = {
  draft: 'Rascunho',
  active: 'Ativo',
  archived: 'Arquivado',
}

interface FormState {
  kind: CreativeItemKind
  name: string
  description: string
  canonicalPrompt: string
  negativePrompt: string
  visibility: CreativeVisibility
  status: CreativeStatus
  rightsConfirmed: boolean
  originalAuthor: string
  licenseNotes: string
  field1: string
  field2: string
  field3: string
  field4: string
  field5: string
  mandatory: string
  prohibited: string
}

const initialForm: FormState = {
  kind: 'character',
  name: '',
  description: '',
  canonicalPrompt: '',
  negativePrompt: '',
  visibility: 'private',
  status: 'draft',
  rightsConfirmed: false,
  originalAuthor: '',
  licenseNotes: '',
  field1: '',
  field2: '',
  field3: '',
  field4: '',
  field5: '',
  mandatory: '',
  prohibited: '',
}

function lines(value: string) {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

function profileFromForm(form: FormState): Record<string, unknown> {
  if (form.kind === 'character') {
    return {
      age_range: form.field1,
      physical_description: form.field2,
      personality: form.field3,
      speaking_style: form.field4,
      pedagogical_role: form.field5,
      mandatory_features: lines(form.mandatory),
      prohibited_features: lines(form.prohibited),
    }
  }
  if (form.kind === 'scene') {
    return {
      setting_type: form.field1,
      period: form.field2,
      location_context: form.field3,
      atmosphere: form.field4,
      pedagogical_use: form.field5,
      mandatory_elements: lines(form.mandatory),
      prohibited_elements: lines(form.prohibited),
    }
  }
  return {
    style_category: form.field1,
    visual_language: form.field2,
    narrative_tone: form.field3,
    pedagogical_tone: form.field4,
    recommended_age_group: form.field5,
    palette_and_rules: lines(form.mandatory),
    avoid: lines(form.prohibited),
  }
}

function formFromItem(item: CreativeItem): FormState {
  const data = item.profile_data
  if (item.kind === 'character') {
    return {
      ...initialForm,
      kind: item.kind,
      name: item.name,
      description: item.description ?? '',
      canonicalPrompt: item.canonical_prompt ?? '',
      negativePrompt: item.negative_prompt ?? '',
      visibility: item.visibility,
      status: item.status,
      rightsConfirmed: item.rights_confirmed,
      originalAuthor: item.original_author ?? '',
      licenseNotes: item.license_notes ?? '',
      field1: String(data.age_range ?? ''),
      field2: String(data.physical_description ?? ''),
      field3: String(data.personality ?? ''),
      field4: String(data.speaking_style ?? ''),
      field5: String(data.pedagogical_role ?? ''),
      mandatory: Array.isArray(data.mandatory_features)
        ? data.mandatory_features.join('\n')
        : '',
      prohibited: Array.isArray(data.prohibited_features)
        ? data.prohibited_features.join('\n')
        : '',
    }
  }
  if (item.kind === 'scene') {
    return {
      ...initialForm,
      kind: item.kind,
      name: item.name,
      description: item.description ?? '',
      canonicalPrompt: item.canonical_prompt ?? '',
      negativePrompt: item.negative_prompt ?? '',
      visibility: item.visibility,
      status: item.status,
      rightsConfirmed: item.rights_confirmed,
      originalAuthor: item.original_author ?? '',
      licenseNotes: item.license_notes ?? '',
      field1: String(data.setting_type ?? ''),
      field2: String(data.period ?? ''),
      field3: String(data.location_context ?? ''),
      field4: String(data.atmosphere ?? ''),
      field5: String(data.pedagogical_use ?? ''),
      mandatory: Array.isArray(data.mandatory_elements)
        ? data.mandatory_elements.join('\n')
        : '',
      prohibited: Array.isArray(data.prohibited_elements)
        ? data.prohibited_elements.join('\n')
        : '',
    }
  }
  return {
    ...initialForm,
    kind: item.kind,
    name: item.name,
    description: item.description ?? '',
    canonicalPrompt: item.canonical_prompt ?? '',
    negativePrompt: item.negative_prompt ?? '',
    visibility: item.visibility,
    status: item.status,
    rightsConfirmed: item.rights_confirmed,
    originalAuthor: item.original_author ?? '',
    licenseNotes: item.license_notes ?? '',
    field1: String(data.style_category ?? ''),
    field2: String(data.visual_language ?? ''),
    field3: String(data.narrative_tone ?? ''),
    field4: String(data.pedagogical_tone ?? ''),
    field5: String(data.recommended_age_group ?? ''),
    mandatory: Array.isArray(data.palette_and_rules)
      ? data.palette_and_rules.join('\n')
      : '',
    prohibited: Array.isArray(data.avoid) ? data.avoid.join('\n') : '',
  }
}

export function CreativeLibraryPage() {
  const { user } = useAuth()
  const role = user?.memberships[0]?.role
  const canWrite = ['owner', 'admin', 'teacher'].includes(role ?? '')

  const [catalog, setCatalog] = useState<CreativeCatalog | null>(null)
  const [items, setItems] = useState<CreativeItem[]>([])
  const [activeKind, setActiveKind] = useState<CreativeItemKind>('character')
  const [selected, setSelected] = useState<CreativeItem | null>(null)
  const [editing, setEditing] = useState<CreativeItem | null>(null)
  const [form, setForm] = useState<FormState>(initialForm)
  const [assetRole, setAssetRole] = useState('reference')
  const [pdfPage, setPdfPage] = useState('')
  const [isPrimary, setIsPrimary] = useState(true)
  const [file, setFile] = useState<File | null>(null)
  const [query, setQuery] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function loadData() {
    setError('')
    try {
      const [catalogData, itemData] = await Promise.all([
        api<CreativeCatalog>('/creative/catalog'),
        api<CreativeItem[]>('/creative/items'),
      ])
      setCatalog(catalogData)
      setItems(itemData)
      if (selected) {
        setSelected(itemData.find((item) => item.id === selected.id) ?? null)
      }
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível carregar a Biblioteca Criativa.',
      )
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  useEffect(() => {
    setForm((current) => ({ ...initialForm, kind: activeKind, visibility: current.visibility }))
    setEditing(null)
  }, [activeKind])

  const filtered = useMemo(
    () =>
      items.filter(
        (item) =>
          item.kind === activeKind &&
          (!query ||
            item.name.toLowerCase().includes(query.toLowerCase()) ||
            (item.description ?? '').toLowerCase().includes(query.toLowerCase())),
      ),
    [items, activeKind, query],
  )

  const assetRoles = useMemo(() => {
    if (!catalog) return ['reference']
    if (activeKind === 'character') return catalog.character_asset_roles
    if (activeKind === 'scene') return catalog.scene_asset_roles
    return catalog.style_asset_roles
  }, [catalog, activeKind])

  useEffect(() => {
    setAssetRole(assetRoles[0] ?? 'reference')
  }, [assetRoles])

  function updateForm<K extends keyof FormState>(field: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  function startEdit(item: CreativeItem) {
    setActiveKind(item.kind)
    setEditing(item)
    setSelected(item)
    setForm(formFromItem(item))
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function cancelEdit() {
    setEditing(null)
    setForm({ ...initialForm, kind: activeKind })
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setSuccess('')
    const payload = {
      kind: form.kind,
      name: form.name.trim(),
      description: form.description.trim() || null,
      canonical_prompt: form.canonicalPrompt.trim() || null,
      negative_prompt: form.negativePrompt.trim() || null,
      profile_data: profileFromForm(form),
      visibility: form.visibility,
      status: form.status,
      rights_confirmed: form.rightsConfirmed,
      original_author: form.originalAuthor.trim() || null,
      license_notes: form.licenseNotes.trim() || null,
      ...(editing ? { change_description: 'Perfil atualizado pela Biblioteca Criativa' } : {}),
    }
    try {
      if (editing) {
        await api<CreativeItem>(`/creative/items/${editing.id}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
        setSuccess('Item criativo atualizado e nova versão registrada.')
      } else {
        await api<CreativeItem>('/creative/items', {
          method: 'POST',
          body: JSON.stringify(payload),
        })
        setSuccess('Item criativo criado.')
      }
      cancelEdit()
      await loadData()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao salvar o item.')
    } finally {
      setBusy(false)
    }
  }

  async function uploadAsset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selected || !file) return
    setBusy(true)
    setError('')
    setSuccess('')
    const data = new FormData()
    data.append('file', file)
    data.append('asset_role', assetRole)
    data.append('is_primary', String(isPrimary))
    if (pdfPage) data.append('pdf_page_number', pdfPage)
    try {
      await api<CreativeAsset>(`/creative/items/${selected.id}/assets`, {
        method: 'POST',
        body: data,
      })
      setFile(null)
      setPdfPage('')
      setSuccess('Arquivo de referência enviado.')
      await loadData()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha no upload.')
    } finally {
      setBusy(false)
    }
  }

  async function downloadAsset(asset: CreativeAsset) {
    try {
      const blob = await apiBlob(`/creative/assets/${asset.id}/download`)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = asset.file_name
      link.click()
      URL.revokeObjectURL(url)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha no download.')
    }
  }

  async function deleteAsset(asset: CreativeAsset) {
    if (!window.confirm(`Excluir ${asset.file_name}?`)) return
    try {
      await api<void>(`/creative/assets/${asset.id}`, { method: 'DELETE' })
      await loadData()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao excluir arquivo.')
    }
  }

  async function archiveItem(item: CreativeItem) {
    try {
      await api<CreativeItem>(`/creative/items/${item.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          status: item.status === 'archived' ? 'active' : 'archived',
          change_description: item.status === 'archived' ? 'Item reativado' : 'Item arquivado',
        }),
      })
      await loadData()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao alterar status.')
    }
  }

  const fieldLabels =
    activeKind === 'character'
      ? ['Faixa etária', 'Descrição física', 'Personalidade', 'Modo de falar', 'Papel pedagógico']
      : activeKind === 'scene'
        ? ['Tipo de ambiente', 'Época', 'Localização/contexto', 'Atmosfera', 'Uso pedagógico']
        : ['Categoria do estilo', 'Linguagem visual', 'Tom narrativo', 'Tom pedagógico', 'Faixa etária']

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <span className="eyebrow">BIBLIOTECA CRIATIVA PEDAGÓGICA</span>
          <h1>Personagens, cenários e estilos</h1>
          <p>Cadastre referências reutilizáveis e preserve a consistência de HQs, jogos e animes.</p>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}

      <div className="filter-bar">
        {(['character', 'scene', 'style'] as const).map((kind) => (
          <button
            className={activeKind === kind ? 'filter active' : 'filter'}
            key={kind}
            onClick={() => setActiveKind(kind)}
            type="button"
          >
            {kindLabels[kind]}
          </button>
        ))}
      </div>

      {canWrite ? (
        <form className="panel" onSubmit={submit}>
          <div className="panel-title-row">
            <div>
              <h2>{editing ? `Editar ${form.name}` : `Novo item: ${kindLabels[activeKind]}`}</h2>
              <p>Os dados estruturados serão reutilizados pelos geradores mock e reais.</p>
            </div>
            {editing ? <button onClick={cancelEdit} type="button">Cancelar edição</button> : null}
          </div>
          <div className="form-grid studio-two-columns">
            <label>
              Nome
              <input value={form.name} onChange={(event) => updateForm('name', event.target.value)} required />
            </label>
            <label>
              Visibilidade
              <select
                value={form.visibility}
                onChange={(event) => updateForm('visibility', event.target.value as CreativeVisibility)}
              >
                {Object.entries(visibilityLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>
            <label>
              Status
              <select
                value={form.status}
                onChange={(event) => updateForm('status', event.target.value as CreativeStatus)}
              >
                {Object.entries(statusLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>
            <label>
              Autor original
              <input value={form.originalAuthor} onChange={(event) => updateForm('originalAuthor', event.target.value)} />
            </label>
            <label className="full-width">
              Descrição
              <textarea rows={3} value={form.description} onChange={(event) => updateForm('description', event.target.value)} />
            </label>
            {fieldLabels.map((label, index) => {
              const field = `field${index + 1}` as 'field1' | 'field2' | 'field3' | 'field4' | 'field5'
              return (
                <label key={label}>
                  {label}
                  <textarea rows={2} value={form[field]} onChange={(event) => updateForm(field, event.target.value)} />
                </label>
              )
            })}
            <label>
              Características/elementos obrigatórios
              <textarea rows={5} value={form.mandatory} onChange={(event) => updateForm('mandatory', event.target.value)} placeholder="Uma regra por linha" />
            </label>
            <label>
              Elementos proibidos
              <textarea rows={5} value={form.prohibited} onChange={(event) => updateForm('prohibited', event.target.value)} placeholder="Uma regra por linha" />
            </label>
            <label>
              Prompt canônico futuro
              <textarea rows={4} value={form.canonicalPrompt} onChange={(event) => updateForm('canonicalPrompt', event.target.value)} />
            </label>
            <label>
              Prompt negativo futuro
              <textarea rows={4} value={form.negativePrompt} onChange={(event) => updateForm('negativePrompt', event.target.value)} />
            </label>
            <label className="full-width">
              Licença e restrições de uso
              <textarea rows={3} value={form.licenseNotes} onChange={(event) => updateForm('licenseNotes', event.target.value)} />
            </label>
          </div>
          <label className="checkbox-row">
            <input
              checked={form.rightsConfirmed}
              onChange={(event) => updateForm('rightsConfirmed', event.target.checked)}
              type="checkbox"
            />
            Confirmo que tenho autorização para utilizar, adaptar e gerar materiais com estas referências
          </label>
          <button className="primary" disabled={busy} type="submit">
            {busy ? 'Salvando...' : editing ? 'Salvar e criar versão' : 'Cadastrar item'}
          </button>
        </form>
      ) : null}

      <section className="panel">
        <div className="panel-title-row">
          <div>
            <h2>{kindLabels[activeKind]}</h2>
            <p>{filtered.length} item(ns) disponível(is).</p>
          </div>
          <input
            aria-label="Pesquisar biblioteca"
            placeholder="Pesquisar..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        <div className="creative-grid">
          {filtered.map((item) => (
            <article className="creative-card" key={item.id}>
              <div className="project-card-heading">
                <div>
                  <strong>{item.name}</strong>
                  <p>{item.description || 'Sem descrição.'}</p>
                </div>
                <span className={`status-chip ${item.status}`}>{statusLabels[item.status]}</span>
              </div>
              <div className="generation-meta">
                <span>Autor: {item.created_by_name_snapshot}</span>
                <span>Visibilidade: {visibilityLabels[item.visibility]}</span>
                <span>Arquivos: {item.assets.length}</span>
                <span>Versões: {item.versions.length}</span>
              </div>
              <div className="card-actions">
                <button onClick={() => setSelected(item)} type="button">Abrir</button>
                {canWrite ? <button onClick={() => startEdit(item)} type="button">Editar</button> : null}
                {canWrite ? <button onClick={() => void archiveItem(item)} type="button">{item.status === 'archived' ? 'Reativar' : 'Arquivar'}</button> : null}
              </div>
            </article>
          ))}
          {filtered.length === 0 ? <p>Nenhum item cadastrado nesta categoria.</p> : null}
        </div>
      </section>

      {selected ? (
        <section className="panel">
          <div className="panel-title-row">
            <div>
              <h2>{selected.name}</h2>
              <p>Referências visuais, fichas PDF e histórico de versões.</p>
            </div>
            <button onClick={() => setSelected(null)} type="button">Fechar</button>
          </div>
          <pre className="proposal-json">{JSON.stringify(selected.profile_data, null, 2)}</pre>

          {canWrite ? (
            <form className="subpanel" onSubmit={uploadAsset}>
              <h3>Enviar referência</h3>
              <div className="form-grid studio-three-columns">
                <label>
                  Arquivo
                  <input
                    accept=".png,.jpg,.jpeg,.webp,.pdf"
                    onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                    type="file"
                    required
                  />
                </label>
                <label>
                  Tipo da referência
                  <select value={assetRole} onChange={(event) => setAssetRole(event.target.value)}>
                    {assetRoles.map((roleOption) => (
                      <option key={roleOption} value={roleOption}>{roleOption}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Página do PDF, se aplicável
                  <input min="1" type="number" value={pdfPage} onChange={(event) => setPdfPage(event.target.value)} />
                </label>
              </div>
              <label className="checkbox-row">
                <input checked={isPrimary} onChange={(event) => setIsPrimary(event.target.checked)} type="checkbox" />
                Usar como referência principal
              </label>
              <button className="primary" disabled={busy || !file} type="submit">Enviar arquivo</button>
            </form>
          ) : null}

          <div className="asset-list">
            {selected.assets.map((asset) => (
              <article className="asset-row" key={asset.id}>
                <div>
                  <strong>{asset.file_name}</strong>
                  <p>{asset.asset_role} • {(asset.size_bytes / 1024).toFixed(1)} KB {asset.is_primary ? '• principal' : ''}</p>
                </div>
                <div className="card-actions">
                  <button onClick={() => void downloadAsset(asset)} type="button">Baixar</button>
                  {canWrite ? <button className="danger-button" onClick={() => void deleteAsset(asset)} type="button">Excluir</button> : null}
                </div>
              </article>
            ))}
            {selected.assets.length === 0 ? <p>Nenhuma referência enviada.</p> : null}
          </div>
        </section>
      ) : null}
    </section>
  )
}
