import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import type { DocumentChapter, DocumentItem } from '../types/document'
import type { Project, Subject } from '../types/education'
import type {
  AssessmentDesign,
  DifficultyLevel,
  FidelityLevel,
  GenerationProject,
  GenerationStatus,
  IntegrationMode,
  PedagogyCatalog,
  PillarRecommendation,
  PrivacyLevel,
  SourceMode,
} from '../types/pedagogy'

const sourceModeLabels: Record<SourceMode, { title: string; description: string }> = {
  document: {
    title: 'Usar PDF',
    description: 'Utiliza documento, capítulo e futuramente unidades confirmadas.',
  },
  ai: {
    title: 'Gerar com IA',
    description: 'Parte de disciplina, tema e objetivos, sem documento obrigatório.',
  },
  teacher_text: {
    title: 'História do professor',
    description: 'Transforma um texto ou roteiro escrito pelo professor.',
  },
  hybrid: {
    title: 'Combinar fontes',
    description: 'Integra PDF, história docente, instruções e complementação da IA.',
  },
}

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

const accessibilityLabels: Record<string, string> = {
  alt_text: 'Descrição alternativa de imagens',
  large_font: 'Fonte ampliada',
  high_contrast: 'Alto contraste',
  black_and_white: 'Versão em preto e branco',
  simplified_language: 'Linguagem simplificada',
  audio_description: 'Audiodescrição',
  captions: 'Legendas',
  screen_reader: 'Compatível com leitor de tela',
  dyslexia_friendly: 'Formatação amigável à dislexia',
  bilingual: 'Material bilíngue',
}

const assessmentLabels: Record<AssessmentDesign, string> = {
  none: 'Sem desenho de avaliação definido',
  diagnostic: 'Avaliação diagnóstica',
  pre_post: 'Pré-teste e pós-teste',
  experimental_control: 'Grupo experimental e controle',
  formative: 'Avaliação formativa',
  summative: 'Avaliação somativa',
  tam: 'Questionário de aceitação/TAM',
}

const statusLabels: Record<GenerationStatus, string> = {
  draft: 'Rascunho',
  in_review: 'Em revisão',
  confirmed: 'Confirmado',
  archived: 'Arquivado',
}

const cognitiveLabels: Record<string, string> = {
  remember: 'Lembrar',
  understand: 'Compreender',
  apply: 'Aplicar',
  analyze: 'Analisar',
  evaluate: 'Avaliar',
  create: 'Criar',
}

interface FormState {
  title: string
  sourceMode: SourceMode
  projectId: string
  subjectId: string
  customSubject: string
  schoolYear: string
  topic: string
  disciplinaryObjective: string
  ctObjective: string
  teacherText: string
  teacherInstructions: string
  allowAiExpansion: boolean
  fidelity: FidelityLevel
  integrationMode: IntegrationMode
  difficulty: DifficultyLevel
  privacy: PrivacyLevel
  creditName: string
  rightsConfirmed: boolean
  bnccSkills: string
  assessmentDesign: AssessmentDesign
  assessmentNotes: string
  measurableObjectives: string
  evaluationVariable: string
  evaluationGroups: string
  showCreditOnCover: boolean
  documentId: string
  chapterId: string
}

const initialForm: FormState = {
  title: '',
  sourceMode: 'document',
  projectId: '',
  subjectId: '',
  customSubject: '',
  schoolYear: '',
  topic: '',
  disciplinaryObjective: '',
  ctObjective: '',
  teacherText: '',
  teacherInstructions: '',
  allowAiExpansion: true,
  fidelity: 'balanced',
  integrationMode: 'balanced',
  difficulty: 'intermediate',
  privacy: 'private',
  creditName: '',
  rightsConfirmed: false,
  bnccSkills: '',
  assessmentDesign: 'none',
  assessmentNotes: '',
  measurableObjectives: '',
  evaluationVariable: '',
  evaluationGroups: '',
  showCreditOnCover: true,
  documentId: '',
  chapterId: '',
}

export function PedagogicalStudioPage() {
  const { user } = useAuth()
  const role = user?.memberships[0]?.role
  const canWrite = ['owner', 'admin', 'teacher'].includes(role ?? '')

  const [catalog, setCatalog] = useState<PedagogyCatalog | null>(null)
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [chapters, setChapters] = useState<DocumentChapter[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [generationProjects, setGenerationProjects] = useState<GenerationProject[]>([])
  const [form, setForm] = useState<FormState>(initialForm)
  const [selectedPillars, setSelectedPillars] = useState<string[]>([])
  const [selectedMaterials, setSelectedMaterials] = useState<string[]>([])
  const [accessibility, setAccessibility] = useState<string[]>([])
  const [selectedCognitiveLevels, setSelectedCognitiveLevels] = useState<string[]>([])
  const [recommendations, setRecommendations] = useState<PillarRecommendation[]>([])
  const [selectedProject, setSelectedProject] = useState<GenerationProject | null>(null)
  const [statusFilter, setStatusFilter] = useState<'all' | GenerationStatus>('all')
  const [busy, setBusy] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function loadData() {
    setError('')
    try {
      const [catalogData, subjectData, documentData, projectData, generationData] =
        await Promise.all([
          api<PedagogyCatalog>('/pedagogy/catalog'),
          api<Subject[]>('/subjects'),
          api<DocumentItem[]>('/documents'),
          api<Project[]>('/projects'),
          api<GenerationProject[]>('/generation-projects'),
        ])
      setCatalog(catalogData)
      setSubjects(subjectData.filter((subject) => subject.is_active))
      setDocuments(documentData.filter((document) => document.status === 'ready'))
      setProjects(projectData)
      setGenerationProjects(generationData)
      if (!form.creditName && user?.full_name) {
        setForm((current) => ({ ...current, creditName: user.full_name }))
      }
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível carregar o estúdio pedagógico.',
      )
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  useEffect(() => {
    if (!form.documentId) {
      setChapters([])
      setForm((current) => ({ ...current, chapterId: '' }))
      return
    }
    void api<DocumentChapter[]>(`/documents/${form.documentId}/chapters`)
      .then((items) => {
        setChapters(items.filter((chapter) => chapter.is_confirmed))
        setForm((current) => ({ ...current, chapterId: '' }))
      })
      .catch((caughtError: unknown) => {
        setError(
          caughtError instanceof Error
            ? caughtError.message
            : 'Não foi possível carregar os capítulos.',
        )
      })
  }, [form.documentId])

  const filteredProjects = useMemo(
    () =>
      statusFilter === 'all'
        ? generationProjects
        : generationProjects.filter((project) => project.status === statusFilter),
    [generationProjects, statusFilter],
  )

  function toggleListItem(
    value: string,
    items: string[],
    setter: (items: string[]) => void,
  ) {
    setter(items.includes(value) ? items.filter((item) => item !== value) : [...items, value])
  }

  function updateForm<Key extends keyof FormState>(key: Key, value: FormState[Key]) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  async function recommendPillars() {
    const selectedSubject = subjects.find((subject) => subject.id === form.subjectId)
    const subjectName =
      form.subjectId === '__custom__'
        ? form.customSubject
        : selectedSubject?.name ?? ''
    if (!subjectName || !form.topic.trim()) {
      setError('Informe a disciplina e o tema antes de solicitar recomendações.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const result = await api<PillarRecommendation[]>('/pedagogy/recommend-pillars', {
        method: 'POST',
        body: JSON.stringify({ subject_name: subjectName, topic: form.topic.trim() }),
      })
      setRecommendations(result)
      setSelectedPillars(result.map((item) => item.pillar_id))
      setSuccess('Pilares recomendados e selecionados. Revise antes de salvar.')
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível recomendar os pilares.',
      )
    } finally {
      setBusy(false)
    }
  }

  function buildSources() {
    const sources: Array<Record<string, unknown>> = []
    if (form.documentId && ['document', 'hybrid'].includes(form.sourceMode)) {
      sources.push({
        source_type: 'document',
        document_id: form.documentId,
        chapter_id: form.chapterId || null,
        learning_unit_id: null,
        content_text: null,
        instructions: form.teacherInstructions.trim() || null,
        priority: 1,
        weight: 1,
        is_primary: true,
        allow_ai_expansion: form.allowAiExpansion,
      })
    }
    if (form.teacherText.trim() && ['teacher_text', 'hybrid'].includes(form.sourceMode)) {
      sources.push({
        source_type: 'teacher_text',
        document_id: null,
        chapter_id: null,
        learning_unit_id: null,
        content_text: form.teacherText.trim(),
        instructions: form.teacherInstructions.trim() || null,
        priority: sources.length + 1,
        weight: 1,
        is_primary: sources.length === 0,
        allow_ai_expansion: form.allowAiExpansion,
      })
    }
    if (form.sourceMode === 'ai' || (form.sourceMode === 'hybrid' && form.allowAiExpansion)) {
      sources.push({
        source_type: 'ai_knowledge',
        document_id: null,
        chapter_id: null,
        learning_unit_id: null,
        content_text: null,
        instructions: form.teacherInstructions.trim() || null,
        priority: sources.length + 1,
        weight: form.sourceMode === 'ai' ? 1 : 0.5,
        is_primary: sources.length === 0,
        allow_ai_expansion: true,
      })
    }
    if (form.teacherInstructions.trim()) {
      sources.push({
        source_type: 'manual_instruction',
        document_id: null,
        chapter_id: null,
        learning_unit_id: null,
        content_text: null,
        instructions: form.teacherInstructions.trim(),
        priority: 0,
        weight: 1,
        is_primary: false,
        allow_ai_expansion: form.allowAiExpansion,
      })
    }
    return sources
  }

  async function createGenerationProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setSuccess('')
    const customSubject = form.subjectId === '__custom__' ? form.customSubject.trim() : null
    const payload = {
      title: form.title.trim(),
      project_id: form.projectId || null,
      source_mode: form.sourceMode,
      subject_id: form.subjectId && form.subjectId !== '__custom__' ? form.subjectId : null,
      custom_subject_name: customSubject,
      school_year: form.schoolYear.trim() || null,
      topic: form.topic.trim(),
      disciplinary_objective: form.disciplinaryObjective.trim() || null,
      computational_thinking_objective: form.ctObjective.trim() || null,
      teacher_text: form.teacherText.trim() || null,
      teacher_instructions: form.teacherInstructions.trim() || null,
      allow_ai_expansion: form.allowAiExpansion,
      fidelity_level: form.fidelity,
      integration_mode: form.integrationMode,
      difficulty_level: form.difficulty,
      privacy_level: form.privacy,
      credit_name: form.creditName.trim() || user?.full_name,
      rights_confirmed: form.rightsConfirmed,
      bncc_skills: form.bnccSkills
        .split(',')
        .map((item) => item.trim().toUpperCase())
        .filter(Boolean),
      desired_materials: selectedMaterials,
      accessibility_options: accessibility,
      source_priority: buildSources().map((source) => String(source.source_type)),
      assessment_design: form.assessmentDesign,
      assessment_notes: form.assessmentNotes.trim() || null,
      cognitive_levels: selectedCognitiveLevels,
      measurable_objectives: form.measurableObjectives
        .split('\n')
        .map((item) => item.trim())
        .filter(Boolean),
      evaluation_plan: {
        dependent_variable: form.evaluationVariable.trim(),
        groups_or_moments: form.evaluationGroups
          .split('\n')
          .map((item) => item.trim())
          .filter(Boolean),
      },
      author_credit_settings: {
        show_on_cover: form.showCreditOnCover,
        show_in_metadata: true,
      },
      status: 'draft',
      pillars: selectedPillars.map((pillarId) => {
        const recommendation = recommendations.find((item) => item.pillar_id === pillarId)
        return {
          pillar_id: pillarId,
          relevance: recommendation?.relevance ?? 'high',
          application_description: recommendation?.justification ?? null,
        }
      }),
      sources: buildSources(),
    }

    try {
      const created = await api<GenerationProject>('/generation-projects', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      setSuccess('Projeto de geração salvo. Agora você pode gerar a proposta mock.')
      setSelectedProject(created)
      setForm({ ...initialForm, creditName: user?.full_name ?? '' })
      setSelectedPillars([])
      setSelectedMaterials([])
      setAccessibility([])
      setSelectedCognitiveLevels([])
      setRecommendations([])
      await loadData()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível salvar o projeto de geração.',
      )
    } finally {
      setBusy(false)
    }
  }

  async function generateMock(project: GenerationProject) {
    setBusyId(project.id)
    setError('')
    try {
      const result = await api<{ generation_project_id: string; proposal: Record<string, unknown> }>(
        `/generation-projects/${project.id}/mock-proposal`,
        { method: 'POST' },
      )
      setSelectedProject({ ...project, status: 'in_review', mock_proposal: result.proposal })
      setSuccess('Proposta pedagógica mock gerada e encaminhada para revisão.')
      await loadData()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível gerar a proposta mock.',
      )
    } finally {
      setBusyId(null)
    }
  }

  async function updateStatus(project: GenerationProject, status: GenerationStatus) {
    setBusyId(project.id)
    setError('')
    try {
      await api<GenerationProject>(`/generation-projects/${project.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      })
      setSuccess(`Projeto atualizado para “${statusLabels[status]}”.`)
      await loadData()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível atualizar o projeto.',
      )
    } finally {
      setBusyId(null)
    }
  }

  async function removeProject(project: GenerationProject) {
    if (!window.confirm(`Excluir o projeto “${project.title}”?`)) return
    setBusyId(project.id)
    setError('')
    try {
      await api<void>(`/generation-projects/${project.id}`, { method: 'DELETE' })
      if (selectedProject?.id === project.id) setSelectedProject(null)
      setSuccess('Projeto de geração excluído.')
      await loadData()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível excluir o projeto.',
      )
    } finally {
      setBusyId(null)
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <span className="eyebrow">SPRINT 04.2</span>
          <h1>Estúdio pedagógico</h1>
          <p>
            Planeje materiais interdisciplinares usando PDF, conhecimento da IA,
            história escrita pelo professor ou uma combinação de fontes. O conteúdo
            permanece mock até as próximas sprints.
          </p>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}

      {!canWrite ? (
        <section className="panel permission-panel">
          <h2>Modo de consulta</h2>
          <p>Seu papel permite consultar projetos, mas não criar ou editar.</p>
        </section>
      ) : (
        <form className="panel studio-form" onSubmit={createGenerationProject}>
          <div className="panel-title-row">
            <div>
              <h2>Novo projeto de geração</h2>
              <p>Defina fonte, disciplina, pilares, autoria e critérios de avaliação.</p>
            </div>
          </div>

          <fieldset className="studio-fieldset">
            <legend>1. Origem do conteúdo</legend>
            <div className="source-mode-grid">
              {(Object.keys(sourceModeLabels) as SourceMode[]).map((mode) => (
                <button
                  className={form.sourceMode === mode ? 'source-mode-card selected' : 'source-mode-card'}
                  key={mode}
                  onClick={() => updateForm('sourceMode', mode)}
                  type="button"
                >
                  <strong>{sourceModeLabels[mode].title}</strong>
                  <span>{sourceModeLabels[mode].description}</span>
                </button>
              ))}
            </div>
          </fieldset>

          <div className="form-grid studio-two-columns">
            <label>
              Título do projeto
              <input
                value={form.title}
                onChange={(event) => updateForm('title', event.target.value)}
                placeholder="Ex.: A missão das frações"
                required
              />
            </label>
            <label>
              Projeto educacional relacionado
              <select
                value={form.projectId}
                onChange={(event) => updateForm('projectId', event.target.value)}
              >
                <option value="">Sem vínculo</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>{project.title}</option>
                ))}
              </select>
            </label>
            <label>
              Disciplina
              <select
                value={form.subjectId}
                onChange={(event) => updateForm('subjectId', event.target.value)}
                required
              >
                <option value="">Selecione</option>
                {subjects.map((subject) => (
                  <option key={subject.id} value={subject.id}>
                    {subject.name} ({subject.code})
                  </option>
                ))}
                <option value="__custom__">Outra disciplina...</option>
              </select>
            </label>
            {form.subjectId === '__custom__' ? (
              <label>
                Nome da disciplina personalizada
                <input
                  value={form.customSubject}
                  onChange={(event) => updateForm('customSubject', event.target.value)}
                  placeholder="Ex.: Educação Financeira"
                  required
                />
              </label>
            ) : (
              <label>
                Ano ou série
                <input
                  value={form.schoolYear}
                  onChange={(event) => updateForm('schoolYear', event.target.value)}
                  placeholder="Ex.: 6º ano"
                />
              </label>
            )}
            {form.subjectId === '__custom__' ? (
              <label>
                Ano ou série
                <input
                  value={form.schoolYear}
                  onChange={(event) => updateForm('schoolYear', event.target.value)}
                  placeholder="Ex.: 6º ano"
                />
              </label>
            ) : null}
            <label>
              Tema
              <input
                value={form.topic}
                onChange={(event) => updateForm('topic', event.target.value)}
                placeholder="Ex.: Frações equivalentes"
                required
              />
            </label>
          </div>

          {['document', 'hybrid'].includes(form.sourceMode) ? (
            <fieldset className="studio-fieldset">
              <legend>Fonte documental</legend>
              <div className="form-grid studio-two-columns">
                <label>
                  PDF processado
                  <select
                    value={form.documentId}
                    onChange={(event) => updateForm('documentId', event.target.value)}
                    required={form.sourceMode === 'document'}
                  >
                    <option value="">Selecione o documento</option>
                    {documents.map((document) => (
                      <option key={document.id} value={document.id}>
                        {document.original_filename}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Capítulo confirmado
                  <select
                    value={form.chapterId}
                    onChange={(event) => updateForm('chapterId', event.target.value)}
                    disabled={!form.documentId}
                  >
                    <option value="">Documento completo ou capítulo futuro</option>
                    {chapters.map((chapter) => (
                      <option key={chapter.id} value={chapter.id}>
                        {chapter.title} — páginas {chapter.start_page}–{chapter.end_page}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </fieldset>
          ) : null}

          {['teacher_text', 'hybrid'].includes(form.sourceMode) ? (
            <fieldset className="studio-fieldset">
              <legend>História ou roteiro do professor</legend>
              <label className="full-width-label">
                Texto do professor
                <textarea
                  rows={8}
                  value={form.teacherText}
                  onChange={(event) => updateForm('teacherText', event.target.value)}
                  placeholder="Digite uma história completa, uma ideia, cenas ou quadros..."
                  required={form.sourceMode === 'teacher_text'}
                />
              </label>
            </fieldset>
          ) : null}

          <fieldset className="studio-fieldset">
            <legend>2. Objetivos e integração</legend>
            <div className="form-grid studio-two-columns">
              <label>
                Objetivo disciplinar
                <textarea
                  rows={4}
                  value={form.disciplinaryObjective}
                  onChange={(event) => updateForm('disciplinaryObjective', event.target.value)}
                  placeholder="O que o estudante aprenderá na disciplina?"
                />
              </label>
              <label>
                Objetivo de Pensamento Computacional
                <textarea
                  rows={4}
                  value={form.ctObjective}
                  onChange={(event) => updateForm('ctObjective', event.target.value)}
                  placeholder="Qual habilidade de PC será desenvolvida?"
                />
              </label>
              <label>
                Modo de integração
                <select
                  value={form.integrationMode}
                  onChange={(event) => updateForm('integrationMode', event.target.value as IntegrationMode)}
                >
                  <option value="subject_focus">Disciplina como foco principal</option>
                  <option value="computational_thinking_focus">PC como foco principal</option>
                  <option value="balanced">Integração equilibrada</option>
                </select>
              </label>
              <label>
                Habilidades BNCC
                <input
                  value={form.bnccSkills}
                  onChange={(event) => updateForm('bnccSkills', event.target.value)}
                  placeholder="EF06MA07, EF06CO01"
                />
              </label>
            </div>

            <div className="panel-title-row pillar-heading">
              <div>
                <h3>Pilares do Pensamento Computacional</h3>
                <p>Selecione todos ou apenas os pilares adequados ao conteúdo.</p>
              </div>
              <div className="card-actions compact">
                <button
                  type="button"
                  onClick={() => setSelectedPillars(catalog?.pillars.map((pillar) => pillar.id) ?? [])}
                >
                  Selecionar todos
                </button>
                <button type="button" onClick={() => setSelectedPillars([])}>Limpar</button>
                <button disabled={busy} type="button" onClick={() => void recommendPillars()}>
                  Recomendar
                </button>
              </div>
            </div>
            <div className="pillar-grid">
              {catalog?.pillars.map((pillar) => {
                const recommendation = recommendations.find((item) => item.pillar_id === pillar.id)
                return (
                  <label
                    className={selectedPillars.includes(pillar.id) ? 'pillar-card selected' : 'pillar-card'}
                    key={pillar.id}
                  >
                    <input
                      checked={selectedPillars.includes(pillar.id)}
                      onChange={() => toggleListItem(pillar.id, selectedPillars, setSelectedPillars)}
                      type="checkbox"
                    />
                    <strong>{pillar.name}</strong>
                    <span>{pillar.description}</span>
                    {recommendation ? (
                      <small>
                        Recomendação {recommendation.relevance}: {recommendation.justification}
                      </small>
                    ) : null}
                  </label>
                )
              })}
            </div>
          </fieldset>

          <fieldset className="studio-fieldset">
            <legend>3. Materiais, fidelidade e acessibilidade</legend>
            <div className="option-grid">
              {catalog?.material_types.map((material) => (
                <label className="option-check" key={material}>
                  <input
                    checked={selectedMaterials.includes(material)}
                    onChange={() => toggleListItem(material, selectedMaterials, setSelectedMaterials)}
                    type="checkbox"
                  />
                  {materialLabels[material] ?? material}
                </label>
              ))}
            </div>
            <div className="form-grid studio-three-columns">
              <label>
                Fidelidade às fontes
                <select
                  value={form.fidelity}
                  onChange={(event) => updateForm('fidelity', event.target.value as FidelityLevel)}
                >
                  <option value="strict">Estrita — somente fontes fornecidas</option>
                  <option value="balanced">Equilibrada — explicações complementares</option>
                  <option value="creative">Criativa — liberdade narrativa controlada</option>
                </select>
              </label>
              <label>
                Dificuldade
                <select
                  value={form.difficulty}
                  onChange={(event) => updateForm('difficulty', event.target.value as DifficultyLevel)}
                >
                  <option value="introductory">Introdutória</option>
                  <option value="basic">Básica</option>
                  <option value="intermediate">Intermediária</option>
                  <option value="advanced">Avançada</option>
                </select>
              </label>
              <label>
                Privacidade
                <select
                  value={form.privacy}
                  onChange={(event) => updateForm('privacy', event.target.value as PrivacyLevel)}
                >
                  <option value="private">Privado</option>
                  <option value="team">Equipe</option>
                  <option value="classroom">Turma</option>
                  <option value="organization">Organização</option>
                </select>
              </label>
            </div>
            <div className="option-grid accessibility-grid">
              {catalog?.accessibility_options.map((option) => (
                <label className="option-check" key={option}>
                  <input
                    checked={accessibility.includes(option)}
                    onChange={() => toggleListItem(option, accessibility, setAccessibility)}
                    type="checkbox"
                  />
                  {accessibilityLabels[option] ?? option}
                </label>
              ))}
            </div>
          </fieldset>

          <fieldset className="studio-fieldset">
            <legend>4. Níveis cognitivos e objetivos mensuráveis</legend>
            <p>Defina o tipo de aprendizagem esperada e os resultados que poderão ser avaliados.</p>
            <div className="option-grid">
              {Object.entries(cognitiveLabels).map(([value, label]) => (
                <label className="option-check" key={value}>
                  <input
                    checked={selectedCognitiveLevels.includes(value)}
                    onChange={() =>
                      toggleListItem(
                        value,
                        selectedCognitiveLevels,
                        setSelectedCognitiveLevels,
                      )
                    }
                    type="checkbox"
                  />
                  {label}
                </label>
              ))}
            </div>
            <div className="form-grid studio-two-columns">
              <label>
                Objetivos mensuráveis
                <textarea
                  rows={5}
                  value={form.measurableObjectives}
                  onChange={(event) => updateForm('measurableObjectives', event.target.value)}
                  placeholder="Um objetivo por linha. Ex.: identificar padrões em frações equivalentes."
                />
              </label>
              <label>
                Variável principal da avaliação
                <textarea
                  rows={5}
                  value={form.evaluationVariable}
                  onChange={(event) => updateForm('evaluationVariable', event.target.value)}
                  placeholder="Ex.: nota de reconhecimento de padrões no pré e pós-teste."
                />
              </label>
              <label className="full-width">
                Grupos ou momentos previstos
                <textarea
                  rows={4}
                  value={form.evaluationGroups}
                  onChange={(event) => updateForm('evaluationGroups', event.target.value)}
                  placeholder="Um por linha: pré-teste, pós-teste, grupo experimental, grupo controle..."
                />
              </label>
            </div>
          </fieldset>

          <fieldset className="studio-fieldset">
            <legend>5. Autoria, instruções e avaliação</legend>
            <div className="form-grid studio-two-columns">
              <label>
                Nome nos créditos
                <input
                  value={form.creditName}
                  onChange={(event) => updateForm('creditName', event.target.value)}
                  placeholder={user?.full_name}
                />
              </label>
              <label>
                Desenho de avaliação futuro
                <select
                  value={form.assessmentDesign}
                  onChange={(event) => updateForm('assessmentDesign', event.target.value as AssessmentDesign)}
                >
                  {(catalog?.assessment_designs ?? []).map((design) => (
                    <option key={design} value={design}>
                      {assessmentLabels[design as AssessmentDesign] ?? design}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Instruções adicionais
                <textarea
                  rows={5}
                  value={form.teacherInstructions}
                  onChange={(event) => updateForm('teacherInstructions', event.target.value)}
                  placeholder="Personagens, cenário, linguagem, cuidados pedagógicos..."
                />
              </label>
              <label>
                Notas sobre avaliação
                <textarea
                  rows={5}
                  value={form.assessmentNotes}
                  onChange={(event) => updateForm('assessmentNotes', event.target.value)}
                  placeholder="Ex.: aplicar pré e pós-teste na mesma turma."
                />
              </label>
            </div>
            <label className="checkbox-row studio-checkbox">
              <input
                checked={form.allowAiExpansion}
                onChange={(event) => updateForm('allowAiExpansion', event.target.checked)}
                type="checkbox"
              />
              Permitir complementação da IA conforme o nível de fidelidade
            </label>
            <label className="checkbox-row studio-checkbox">
              <input
                checked={form.showCreditOnCover}
                onChange={(event) => updateForm('showCreditOnCover', event.target.checked)}
                type="checkbox"
              />
              Exibir autoria na capa e nas exportações futuras
            </label>
            <label className="checkbox-row studio-checkbox">
              <input
                checked={form.rightsConfirmed}
                onChange={(event) => updateForm('rightsConfirmed', event.target.checked)}
                type="checkbox"
              />
              Confirmo que tenho autorização para utilizar e transformar as fontes fornecidas
            </label>
          </fieldset>

          <button className="primary studio-submit" disabled={busy} type="submit">
            {busy ? 'Salvando...' : 'Salvar projeto de geração'}
          </button>
        </form>
      )}

      <section className="panel">
        <div className="panel-title-row">
          <div>
            <h2>Projetos planejados</h2>
            <p>Autoria, fontes, pilares e desenho de avaliação ficam registrados.</p>
          </div>
          <div className="filter-bar">
            {(['all', 'draft', 'in_review', 'confirmed', 'archived'] as const).map((status) => (
              <button
                className={statusFilter === status ? 'filter active' : 'filter'}
                key={status}
                onClick={() => setStatusFilter(status)}
                type="button"
              >
                {status === 'all' ? 'Todos' : statusLabels[status]}
              </button>
            ))}
          </div>
        </div>

        <div className="generation-project-list">
          {filteredProjects.map((project) => (
            <article className="generation-project-card" key={project.id}>
              <div className="project-card-heading">
                <div>
                  <strong>{project.title}</strong>
                  <p>{project.topic}</p>
                </div>
                <span className={`status-chip ${project.status}`}>{statusLabels[project.status]}</span>
              </div>
              <div className="generation-meta">
                <span>Fonte: {sourceModeLabels[project.source_mode].title}</span>
                <span>Autor: {project.created_by_name_snapshot}</span>
                <span>Crédito: {project.credit_name}</span>
                <span>Pilares: {project.pillars.map((pillar) => pillar.name).join(', ')}</span>
                <span>Materiais: {project.desired_materials.map((item) => materialLabels[item] ?? item).join(', ')}</span>
              </div>
              <div className="card-actions">
                <button type="button" onClick={() => setSelectedProject(project)}>Visualizar</button>
                <Link to={`/estudio-pedagogico/${project.id}/criativo`}>Universo criativo</Link>
                {canWrite ? (
                  <button
                    disabled={busyId === project.id}
                    type="button"
                    onClick={() => void generateMock(project)}
                  >
                    Gerar proposta mock
                  </button>
                ) : null}
                {canWrite && project.status === 'in_review' ? (
                  <button
                    disabled={busyId === project.id}
                    type="button"
                    onClick={() => void updateStatus(project, 'confirmed')}
                  >
                    Confirmar
                  </button>
                ) : null}
                {canWrite && project.status !== 'archived' ? (
                  <button
                    disabled={busyId === project.id}
                    type="button"
                    onClick={() => void updateStatus(project, 'archived')}
                  >
                    Arquivar
                  </button>
                ) : null}
                {canWrite ? (
                  <button
                    className="danger-button"
                    disabled={busyId === project.id}
                    type="button"
                    onClick={() => void removeProject(project)}
                  >
                    Excluir
                  </button>
                ) : null}
              </div>
            </article>
          ))}
          {filteredProjects.length === 0 ? <p>Nenhum projeto encontrado.</p> : null}
        </div>
      </section>

      {selectedProject ? (
        <section className="panel proposal-panel">
          <div className="panel-title-row">
            <div>
              <h2>{selectedProject.title}</h2>
              <p>Pré-visualização do planejamento e da proposta mock.</p>
            </div>
            <button type="button" onClick={() => setSelectedProject(null)}>Fechar</button>
          </div>
          <div className="detail-list">
            <div><span>Gerado por</span><strong>{selectedProject.created_by_name_snapshot}</strong></div>
            <div><span>Objetivo disciplinar</span><strong>{selectedProject.disciplinary_objective ?? 'Não informado'}</strong></div>
            <div><span>Objetivo de PC</span><strong>{selectedProject.computational_thinking_objective ?? 'Não informado'}</strong></div>
            <div><span>Avaliação</span><strong>{assessmentLabels[selectedProject.assessment_design]}</strong></div>
            <div><span>Níveis cognitivos</span><strong>{selectedProject.cognitive_levels.map((level) => cognitiveLabels[level] ?? level).join(', ') || 'Não definidos'}</strong></div>
            <div><span>Objetivos mensuráveis</span><strong>{selectedProject.measurable_objectives.join('; ') || 'Não definidos'}</strong></div>
          </div>
          {selectedProject.mock_proposal ? (
            <pre className="proposal-json">{JSON.stringify(selectedProject.mock_proposal, null, 2)}</pre>
          ) : (
            <p>A proposta mock ainda não foi gerada.</p>
          )}
        </section>
      ) : null}
    </section>
  )
}
