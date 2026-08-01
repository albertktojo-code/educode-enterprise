import { FormEvent, useEffect, useMemo, useState } from 'react'

import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import type { TeachingSequence, TeachingSequenceItem } from '../types/creative'
import type { GenerationProject, PedagogyCatalog } from '../types/pedagogy'

const materialLabels: Record<string, string> = {
  comic: 'HQ educativa',
  quiz: 'Quiz',
  activity: 'Atividade',
  educational_game: 'Jogo educativo',
  crossword: 'Palavras cruzadas',
  word_search: 'Caça-palavras',
  anime_script: 'Roteiro de anime',
  storyboard: 'Storyboard',
  lesson_plan: 'Plano de aula',
}

const evaluationRoleLabels: Record<string, string> = {
  none: 'Sem função avaliativa',
  pretest: 'Pré-teste',
  intervention: 'Intervenção',
  posttest: 'Pós-teste',
  follow_up: 'Acompanhamento',
}

function blankItem(position: number): TeachingSequenceItem {
  return {
    position,
    title: '',
    material_type: 'comic',
    learning_objective: '',
    pillar_codes: [],
    duration_minutes: 45,
    evaluation_role: 'none',
    notes: '',
  }
}

export function TeachingSequencesPage() {
  const { user } = useAuth()
  const role = user?.memberships[0]?.role
  const canWrite = ['owner', 'admin', 'teacher'].includes(role ?? '')

  const [sequences, setSequences] = useState<TeachingSequence[]>([])
  const [projects, setProjects] = useState<GenerationProject[]>([])
  const [catalog, setCatalog] = useState<PedagogyCatalog | null>(null)
  const [editing, setEditing] = useState<TeachingSequence | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [generationProjectId, setGenerationProjectId] = useState('')
  const [status, setStatus] = useState<'draft' | 'in_review' | 'approved' | 'archived'>('draft')
  const [items, setItems] = useState<TeachingSequenceItem[]>([blankItem(0)])
  const [selected, setSelected] = useState<TeachingSequence | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [busy, setBusy] = useState(false)

  async function loadData() {
    try {
      const [sequenceData, projectData, catalogData] = await Promise.all([
        api<TeachingSequence[]>('/teaching-sequences'),
        api<GenerationProject[]>('/generation-projects'),
        api<PedagogyCatalog>('/pedagogy/catalog'),
      ])
      setSequences(sequenceData)
      setProjects(projectData)
      setCatalog(catalogData)
      if (selected) {
        setSelected(sequenceData.find((item) => item.id === selected.id) ?? null)
      }
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível carregar as sequências didáticas.',
      )
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  const materialTypes = useMemo(() => catalog?.material_types ?? [], [catalog])

  function resetForm() {
    setEditing(null)
    setTitle('')
    setDescription('')
    setGenerationProjectId('')
    setStatus('draft')
    setItems([blankItem(0)])
  }

  function startEdit(sequence: TeachingSequence) {
    setEditing(sequence)
    setTitle(sequence.title)
    setDescription(sequence.description ?? '')
    setGenerationProjectId(sequence.generation_project_id ?? '')
    setStatus(sequence.status)
    setItems(sequence.items.map((item) => ({ ...item })))
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function updateItem(index: number, field: keyof TeachingSequenceItem, value: unknown) {
    setItems((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item,
      ),
    )
  }

  function togglePillar(index: number, code: string) {
    const current = items[index].pillar_codes
    updateItem(
      index,
      'pillar_codes',
      current.includes(code) ? current.filter((item) => item !== code) : [...current, code],
    )
  }

  function addStep() {
    setItems((current) => [...current, blankItem(current.length)])
  }

  function removeStep(index: number) {
    setItems((current) =>
      current
        .filter((_, itemIndex) => itemIndex !== index)
        .map((item, itemIndex) => ({ ...item, position: itemIndex })),
    )
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setSuccess('')
    const payload = {
      generation_project_id: generationProjectId || null,
      title: title.trim(),
      description: description.trim() || null,
      status,
      items: items.map((item, index) => ({
        position: index,
        title: item.title.trim(),
        material_type: item.material_type,
        learning_objective: item.learning_objective?.trim() || null,
        pillar_codes: item.pillar_codes,
        duration_minutes: item.duration_minutes || null,
        evaluation_role: item.evaluation_role,
        notes: item.notes?.trim() || null,
      })),
    }
    try {
      if (editing) {
        await api<TeachingSequence>(`/teaching-sequences/${editing.id}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
        setSuccess('Sequência didática atualizada.')
      } else {
        await api<TeachingSequence>('/teaching-sequences', {
          method: 'POST',
          body: JSON.stringify(payload),
        })
        setSuccess('Sequência didática criada.')
      }
      resetForm()
      await loadData()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao salvar sequência.')
    } finally {
      setBusy(false)
    }
  }

  async function removeSequence(sequence: TeachingSequence) {
    if (!window.confirm(`Excluir a sequência “${sequence.title}”?`)) return
    try {
      await api<void>(`/teaching-sequences/${sequence.id}`, { method: 'DELETE' })
      if (selected?.id === sequence.id) setSelected(null)
      await loadData()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao excluir sequência.')
    }
  }

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <span className="eyebrow">PLANEJAMENTO DE INTERVENÇÃO</span>
          <h1>Sequências didáticas</h1>
          <p>Organize HQ, quiz, jogo, atividade e avaliação em uma jornada coerente.</p>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}

      {canWrite ? (
        <form className="panel" onSubmit={submit}>
          <div className="panel-title-row">
            <div>
              <h2>{editing ? 'Editar sequência' : 'Nova sequência didática'}</h2>
              <p>As etapas podem assumir papel de pré-teste, intervenção ou pós-teste.</p>
            </div>
            {editing ? <button onClick={resetForm} type="button">Cancelar edição</button> : null}
          </div>
          <div className="form-grid studio-two-columns">
            <label>
              Título
              <input value={title} onChange={(event) => setTitle(event.target.value)} required />
            </label>
            <label>
              Projeto do Estúdio Pedagógico
              <select value={generationProjectId} onChange={(event) => setGenerationProjectId(event.target.value)}>
                <option value="">Sem vínculo</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>{project.title}</option>
                ))}
              </select>
            </label>
            <label>
              Status
              <select value={status} onChange={(event) => setStatus(event.target.value as typeof status)}>
                <option value="draft">Rascunho</option>
                <option value="in_review">Em revisão</option>
                <option value="approved">Aprovada</option>
                <option value="archived">Arquivada</option>
              </select>
            </label>
            <label className="full-width">
              Descrição
              <textarea rows={3} value={description} onChange={(event) => setDescription(event.target.value)} />
            </label>
          </div>

          <div className="sequence-editor">
            {items.map((item, index) => (
              <fieldset className="studio-fieldset" key={`${index}-${item.id ?? 'new'}`}>
                <legend>Etapa {index + 1}</legend>
                <div className="form-grid studio-three-columns">
                  <label>
                    Título
                    <input value={item.title} onChange={(event) => updateItem(index, 'title', event.target.value)} required />
                  </label>
                  <label>
                    Material
                    <select value={item.material_type} onChange={(event) => updateItem(index, 'material_type', event.target.value)}>
                      {materialTypes.map((material) => (
                        <option key={material} value={material}>{materialLabels[material] ?? material}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Função na avaliação
                    <select value={item.evaluation_role} onChange={(event) => updateItem(index, 'evaluation_role', event.target.value)}>
                      {Object.entries(evaluationRoleLabels).map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Duração em minutos
                    <input
                      min="1"
                      type="number"
                      value={item.duration_minutes ?? ''}
                      onChange={(event) => updateItem(index, 'duration_minutes', Number(event.target.value) || null)}
                    />
                  </label>
                  <label className="full-width">
                    Objetivo de aprendizagem
                    <textarea rows={2} value={item.learning_objective ?? ''} onChange={(event) => updateItem(index, 'learning_objective', event.target.value)} />
                  </label>
                </div>
                <div className="option-grid">
                  {catalog?.pillars.map((pillar) => (
                    <label className="option-check" key={pillar.code}>
                      <input
                        checked={item.pillar_codes.includes(pillar.code)}
                        onChange={() => togglePillar(index, pillar.code)}
                        type="checkbox"
                      />
                      {pillar.name}
                    </label>
                  ))}
                </div>
                <label>
                  Observações
                  <textarea rows={2} value={item.notes ?? ''} onChange={(event) => updateItem(index, 'notes', event.target.value)} />
                </label>
                {items.length > 1 ? <button className="danger-button" onClick={() => removeStep(index)} type="button">Remover etapa</button> : null}
              </fieldset>
            ))}
          </div>
          <div className="card-actions">
            <button onClick={addStep} type="button">Adicionar etapa</button>
            <button className="primary" disabled={busy} type="submit">{busy ? 'Salvando...' : 'Salvar sequência'}</button>
          </div>
        </form>
      ) : null}

      <section className="panel">
        <h2>Sequências cadastradas</h2>
        <div className="generation-project-list">
          {sequences.map((sequence) => (
            <article className="generation-project-card" key={sequence.id}>
              <div className="project-card-heading">
                <div>
                  <strong>{sequence.title}</strong>
                  <p>{sequence.description || 'Sem descrição.'}</p>
                </div>
                <span className={`status-chip ${sequence.status}`}>{sequence.status}</span>
              </div>
              <div className="generation-meta">
                <span>Autor: {sequence.created_by_name_snapshot}</span>
                <span>Etapas: {sequence.items.length}</span>
                <span>Duração: {sequence.items.reduce((total, item) => total + (item.duration_minutes ?? 0), 0)} min</span>
              </div>
              <div className="card-actions">
                <button onClick={() => setSelected(sequence)} type="button">Visualizar</button>
                {canWrite ? <button onClick={() => startEdit(sequence)} type="button">Editar</button> : null}
                {canWrite ? <button className="danger-button" onClick={() => void removeSequence(sequence)} type="button">Excluir</button> : null}
              </div>
            </article>
          ))}
          {sequences.length === 0 ? <p>Nenhuma sequência cadastrada.</p> : null}
        </div>
      </section>

      {selected ? (
        <section className="panel">
          <div className="panel-title-row">
            <div>
              <h2>{selected.title}</h2>
              <p>Jornada didática completa.</p>
            </div>
            <button onClick={() => setSelected(null)} type="button">Fechar</button>
          </div>
          <ol className="sequence-preview">
            {selected.items.map((item) => (
              <li key={item.id ?? item.position}>
                <strong>{item.title}</strong>
                <span>{materialLabels[item.material_type] ?? item.material_type}</span>
                <p>{item.learning_objective || 'Sem objetivo informado.'}</p>
                <small>{evaluationRoleLabels[item.evaluation_role] ?? item.evaluation_role} • {item.duration_minutes ?? 0} min • {item.pillar_codes.join(', ') || 'sem pilares'}</small>
              </li>
            ))}
          </ol>
        </section>
      ) : null}
    </section>
  )
}
