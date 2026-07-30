import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'
import type { GenerationProject } from '../types/pedagogy'
import type { RagContextSummary } from '../types/rag'
import type {
  ArtDirectionPreset,
  PagePlanItem,
  PedagogicalPackage,
  StudioMaterialType,
  StudioTemplate,
  TeacherStudioDraft,
} from '../types/studio'

const outputLabels: Record<StudioMaterialType, string> = {
  comic: 'HQ',
  quiz: 'Quiz',
  exercise: 'Exercícios',
  activity: 'Atividade',
  game: 'Jogo',
  lesson_plan: 'Plano de aula',
  teaching_sequence: 'Sequência didática',
  answer_key: 'Gabarito',
  teacher_guide: 'Orientações ao professor',
}

const steps = ['Objetivo', 'Material', 'Direção de arte', 'Páginas', 'Revisão']

export function TeacherStudioPage() {
  const [templates, setTemplates] = useState<StudioTemplate[]>([])
  const [presets, setPresets] = useState<ArtDirectionPreset[]>([])
  const [drafts, setDrafts] = useState<TeacherStudioDraft[]>([])
  const [projects, setProjects] = useState<GenerationProject[]>([])
  const [contexts, setContexts] = useState<RagContextSummary[]>([])
  const [packages, setPackages] = useState<PedagogicalPackage[]>([])
  const [step, setStep] = useState(0)
  const [mode, setMode] = useState<'quick' | 'advanced'>('quick')
  const [draftId, setDraftId] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({
    title: '',
    subject_name: 'Matemática',
    school_year: '6º ano',
    topic: '',
    objective: '',
    preset_code: 'cartoon_educational',
    emotional_palette: 'joyful',
    story_pages: 4,
    outputs: ['comic', 'exercise', 'answer_key'] as StudioMaterialType[],
    generation_project_id: '',
    rag_context_id: '',
    accessibility: ['alt_text', 'reading_order'],
  })
  const [pagePlan, setPagePlan] = useState<PagePlanItem[]>([])

  async function load() {
    const [templateData, presetData, draftData, packageData, projectData, contextData] = await Promise.all([
      api<StudioTemplate[]>('/teacher-studio/templates'),
      api<ArtDirectionPreset[]>('/teacher-studio/art-presets'),
      api<TeacherStudioDraft[]>('/teacher-studio/drafts'),
      api<PedagogicalPackage[]>('/teacher-studio/packages'),
      api<GenerationProject[]>('/generation-projects'),
      api<RagContextSummary[]>('/rag-contexts'),
    ])
    setTemplates(templateData)
    setPresets(presetData)
    setDrafts(draftData)
    setPackages(packageData)
    setProjects(projectData)
    setContexts(contextData)
  }

  useEffect(() => {
    void load().catch((error: Error) => setMessage(error.message))
  }, [])

  const selectedPreset = useMemo(
    () => presets.find((item) => item.code === form.preset_code),
    [presets, form.preset_code],
  )
  const availableContexts = useMemo(
    () => contexts.filter((item) => item.generation_project_id === form.generation_project_id && item.status === 'approved'),
    [contexts, form.generation_project_id],
  )

  function toggleOutput(output: StudioMaterialType) {
    setForm((current) => ({
      ...current,
      outputs: current.outputs.includes(output)
        ? current.outputs.filter((item) => item !== output)
        : [...current.outputs, output],
    }))
  }

  function applyTemplate(template: StudioTemplate) {
    setForm((current) => ({
      ...current,
      title: current.title || template.name,
      story_pages: template.story_pages,
      outputs: template.outputs,
    }))
    setMessage(`Modelo “${template.name}” aplicado.`)
  }

  async function ensureDraft(): Promise<string> {
    if (draftId) return draftId
    const created = await api<TeacherStudioDraft>('/teacher-studio/drafts', {
      method: 'POST',
      body: JSON.stringify({
        title: form.title || `${form.topic || 'Novo material'} — ${form.school_year}`,
        creation_mode: mode,
        primary_material: 'comic',
        generation_project_id: form.generation_project_id || null,
        rag_context_id: form.rag_context_id || null,
        subject_name: form.subject_name,
        school_year: form.school_year,
        topic: form.topic,
        objective: form.objective,
        selected_outputs: form.outputs,
        art_direction: {
          preset_code: form.preset_code,
          influence_strength: 'moderate',
          color_mode: selectedPreset?.preview_config.color_mode ?? 'color',
          detail_level: 'medium',
          expression_intensity: 'medium',
          emotional_palette: form.emotional_palette,
          reading_direction: 'left_to_right',
          allow_intentional_style_shifts: true,
          custom_rules: [],
        },
        accessibility_options: form.accessibility,
      }),
    })
    setDraftId(created.id)
    setDrafts((current) => [created, ...current])
    return created.id
  }

  async function recommendPages() {
    setBusy(true)
    setMessage('')
    try {
      const id = await ensureDraft()
      const pages = await api<PagePlanItem[]>(
        `/teacher-studio/drafts/${id}/recommend-pages`,
        {
          method: 'POST',
          body: JSON.stringify({
            story_pages: form.story_pages,
            include_cover: true,
            include_exercises: form.outputs.includes('exercise') || form.outputs.includes('quiz'),
            include_answer_key: form.outputs.includes('answer_key'),
            include_teacher_guide: form.outputs.includes('teacher_guide'),
            narrative_profile: 'balanced',
          }),
        },
      )
      setPagePlan(pages)
      setStep(3)
    } catch (error) {
      setMessage((error as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function generatePackage() {
    setBusy(true)
    setMessage('')
    try {
      const id = await ensureDraft()
      await api(`/teacher-studio/drafts/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          title: form.title,
          current_step: 5,
          selected_outputs: form.outputs,
          page_plan: pagePlan,
          status: 'configured',
        }),
      })
      const created = await api<PedagogicalPackage>(
        `/teacher-studio/drafts/${id}/packages`,
        { method: 'POST', body: JSON.stringify({ outputs: form.outputs }) },
      )
      setPackages((current) => [created, ...current])
      setStep(4)
      setMessage('Pacote pedagógico criado com o mesmo contexto para todos os materiais.')
    } catch (error) {
      setMessage((error as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="teacher-studio-page">
      <header className="teacher-hero">
        <div>
          <span className="eyebrow">Estúdio do Professor</span>
          <h1>Crie materiais sem enfrentar telas técnicas</h1>
          <p>Escolha o objetivo, revise a sugestão e gere um pacote pedagógico coerente.</p>
        </div>
        <div><a className="secondary-button" href="/ia?module=planning&action=generate_lesson_plan">Planejar com IA</a><div className="mode-switch" aria-label="Modo de criação">
          <button className={mode === 'quick' ? 'active' : ''} onClick={() => setMode('quick')} type="button">Modo rápido</button>
          <button className={mode === 'advanced' ? 'active' : ''} onClick={() => setMode('advanced')} type="button">Modo avançado</button>
        </div></div>
      </header>

      <div className="studio-stepper">
        {steps.map((label, index) => (
          <button key={label} className={index === step ? 'active' : index < step ? 'done' : ''} onClick={() => setStep(index)} type="button">
            <span>{index + 1}</span>{label}
          </button>
        ))}
      </div>

      {message ? <div className="inline-message">{message}</div> : null}

      <section className="studio-workspace">
        <div className="studio-main-card">
          {step === 0 ? (
            <div className="studio-form-grid">
              <label className="span-2">Planejamento pedagógico
                <select value={form.generation_project_id} onChange={(event) => {
                  const project = projects.find((item) => item.id === event.target.value)
                  setForm((current) => ({
                    ...current,
                    generation_project_id: event.target.value,
                    rag_context_id: '',
                    title: current.title || project?.title || '',
                    topic: project?.topic || current.topic,
                    school_year: project?.school_year || current.school_year,
                    objective: project?.disciplinary_objective || current.objective,
                  }))
                }}>
                  <option value="">Criar somente o planejamento do pacote</option>
                  {projects.map((project) => <option key={project.id} value={project.id}>{project.title} — {project.topic}</option>)}
                </select>
              </label>
              {form.generation_project_id ? <label className="span-2">Contexto aprovado para gerar a HQ
                <select value={form.rag_context_id} onChange={(event) => setForm({ ...form, rag_context_id: event.target.value })}>
                  <option value="">Selecione um contexto aprovado</option>
                  {availableContexts.map((context) => <option key={context.id} value={context.id}>{context.title} · qualidade {Math.round(context.quality_score)}%</option>)}
                </select>
              </label> : null}
              <label>Título<input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="Ex.: O mistério das frações" /></label>
              <label>Disciplina<input value={form.subject_name} onChange={(event) => setForm({ ...form, subject_name: event.target.value })} /></label>
              <label>Ano/turma<input value={form.school_year} onChange={(event) => setForm({ ...form, school_year: event.target.value })} /></label>
              <label>Tema<input value={form.topic} onChange={(event) => setForm({ ...form, topic: event.target.value })} placeholder="O que deseja ensinar?" /></label>
              <label className="span-2">Objetivo<textarea value={form.objective} onChange={(event) => setForm({ ...form, objective: event.target.value })} placeholder="O que os estudantes devem compreender ou fazer?" /></label>
            </div>
          ) : null}

          {step === 1 ? (
            <div>
              <h2>O que deseja criar?</h2>
              <div className="material-card-grid">
                {(Object.keys(outputLabels) as StudioMaterialType[]).map((output) => (
                  <button key={output} className={form.outputs.includes(output) ? 'material-card selected' : 'material-card'} onClick={() => toggleOutput(output)} type="button">
                    <strong>{outputLabels[output]}</strong>
                    <small>{form.outputs.includes(output) ? 'Incluído no pacote' : 'Clique para incluir'}</small>
                  </button>
                ))}
              </div>
              <h3>Modelos rápidos</h3>
              <div className="template-row">
                {templates.map((template) => <button key={template.code} onClick={() => applyTemplate(template)} type="button"><strong>{template.name}</strong><span>{template.description}</span></button>)}
              </div>
            </div>
          ) : null}

          {step === 2 ? (
            <div>
              <h2>Direção de arte</h2>
              <p>O estilo visual é separado do tom narrativo e pode ser alterado depois.</p>
              <div className="art-preset-grid">
                {presets.map((preset) => (
                  <button key={preset.code} className={preset.code === form.preset_code ? 'art-preset selected' : 'art-preset'} onClick={() => setForm({ ...form, preset_code: preset.code })} type="button">
                    <div className={`art-preview art-${preset.category}`}>{preset.name.slice(0, 2).toUpperCase()}</div>
                    <strong>{preset.name}</strong><span>{preset.description}</span>
                  </button>
                ))}
              </div>
              {mode === 'advanced' ? (
                <div className="studio-form-grid compact">
                  <label>Paleta emocional<select value={form.emotional_palette} onChange={(event) => setForm({ ...form, emotional_palette: event.target.value })}><option value="joyful">Alegre</option><option value="mysterious">Misteriosa</option><option value="emotional">Emocionante</option><option value="dramatic">Dramática</option><option value="futuristic">Futurista</option></select></label>
                  <label>Páginas de história<input min={1} max={24} type="number" value={form.story_pages} onChange={(event) => setForm({ ...form, story_pages: Number(event.target.value) })} /></label>
                </div>
              ) : null}
            </div>
          ) : null}

          {step === 3 ? (
            <div>
              <div className="section-title-row"><div><h2>Planejamento multipágina</h2><p>Altere a quantidade de quadros sem perder a ordem narrativa.</p></div><button onClick={() => void recommendPages()} type="button">Recalcular</button></div>
              <div className="page-plan-strip">
                {pagePlan.map((page) => (
                  <article key={page.page_number} className={`page-plan-card role-${page.role}`}>
                    <span>Página {page.page_number}</span><strong>{page.role.replace('_', ' ')}</strong><small>{page.panel_count} quadro(s)</small><em>{page.narrative_function}</em>
                  </article>
                ))}
              </div>
            </div>
          ) : null}

          {step === 4 ? (
            <div>
              <h2>Pacote pronto para revisão</h2>
              <div className="review-summary">
                <div><span>Tema</span><strong>{form.topic}</strong></div>
                <div><span>Turma</span><strong>{form.school_year}</strong></div>
                <div><span>Estilo</span><strong>{selectedPreset?.name}</strong></div>
                <div><span>Páginas</span><strong>{pagePlan.length || form.story_pages}</strong></div>
              </div>
              <p>Todos os materiais usam o mesmo contexto, objetivo, faixa escolar e direção de arte.</p>
              {packages[0]?.comic_id ? <Link className="primary-link" to={`/canvas/${packages[0].comic_id}`}>Abrir HQ no canvas visual</Link> : <Link to="/hqs">Gerar a HQ a partir de um contexto aprovado</Link>}
            </div>
          ) : null}

          <footer className="wizard-actions">
            <button disabled={step === 0} onClick={() => setStep((current) => Math.max(0, current - 1))} type="button">Voltar</button>
            {step < 2 ? <button className="primary" onClick={() => setStep((current) => current + 1)} type="button">Continuar</button> : null}
            {step === 2 ? <button className="primary" disabled={busy} onClick={() => void recommendPages()} type="button">{busy ? 'Planejando…' : 'Planejar páginas'}</button> : null}
            {step === 3 ? <button className="primary" disabled={busy} onClick={() => void generatePackage()} type="button">{busy ? 'Gerando…' : 'Gerar pacote pedagógico'}</button> : null}
          </footer>
        </div>

        <aside className="studio-side-card">
          <h2>Continuar criação</h2>
          {drafts.slice(0, 4).map((draft) => <button key={draft.id} onClick={() => { setDraftId(draft.id); setForm((current) => ({ ...current, title: draft.title, topic: draft.topic, objective: draft.objective, subject_name: draft.subject_name, school_year: draft.school_year, outputs: draft.selected_outputs, generation_project_id: draft.generation_project_id ?? '', rag_context_id: draft.rag_context_id ?? '' })); setPagePlan(draft.page_plan) }} type="button"><strong>{draft.title}</strong><span>{draft.status} · {draft.current_step}/5</span></button>)}
          <h2>Materiais recentes</h2>
          {packages.slice(0, 4).map((item) => <article key={item.id}><strong>{item.title}</strong><span>{item.materials.length} material(is)</span>{item.comic_id ? <Link to={`/canvas/${item.comic_id}`}>Abrir no canvas</Link> : null}</article>)}
        </aside>
      </section>
    </div>
  )
}
