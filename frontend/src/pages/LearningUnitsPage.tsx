import { FormEvent, useEffect, useState } from 'react'

import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import type { DocumentChapter, DocumentItem } from '../types/document'
import type { Subject } from '../types/education'
import type { DifficultyLevel, LearningUnit } from '../types/pedagogy'

interface UnitForm {
  title: string
  subjectId: string
  description: string
  startPage: string
  endPage: string
  schoolYear: string
  difficulty: DifficultyLevel
  disciplinaryObjective: string
  isConfirmed: boolean
  position: string
}

const initialForm: UnitForm = {
  title: '',
  subjectId: '',
  description: '',
  startPage: '',
  endPage: '',
  schoolYear: '',
  difficulty: 'intermediate',
  disciplinaryObjective: '',
  isConfirmed: false,
  position: '0',
}

const difficultyLabels: Record<DifficultyLevel, string> = {
  introductory: 'Introdutória',
  basic: 'Básica',
  intermediate: 'Intermediária',
  advanced: 'Avançada',
}

export function LearningUnitsPage() {
  const { user } = useAuth()
  const role = user?.memberships[0]?.role
  const canWrite = ['owner', 'admin', 'teacher'].includes(role ?? '')

  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [chapters, setChapters] = useState<DocumentChapter[]>([])
  const [units, setUnits] = useState<LearningUnit[]>([])
  const [documentId, setDocumentId] = useState('')
  const [chapterId, setChapterId] = useState('')
  const [form, setForm] = useState<UnitForm>(initialForm)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    void Promise.all([
      api<DocumentItem[]>('/documents'),
      api<Subject[]>('/subjects'),
    ])
      .then(([documentData, subjectData]) => {
        setDocuments(documentData.filter((document) => document.status === 'ready'))
        setSubjects(subjectData.filter((subject) => subject.is_active))
      })
      .catch((caughtError: unknown) => {
        setError(
          caughtError instanceof Error
            ? caughtError.message
            : 'Não foi possível carregar os dados.',
        )
      })
  }, [])

  useEffect(() => {
    if (!documentId) {
      setChapters([])
      setChapterId('')
      return
    }
    void api<DocumentChapter[]>(`/documents/${documentId}/chapters`)
      .then((data) => {
        setChapters(data.filter((chapter) => chapter.is_confirmed))
        setChapterId('')
      })
      .catch((caughtError: unknown) => {
        setError(caughtError instanceof Error ? caughtError.message : 'Falha ao carregar capítulos.')
      })
  }, [documentId])

  async function loadUnits(selectedChapterId: string) {
    if (!selectedChapterId) {
      setUnits([])
      return
    }
    try {
      setUnits(await api<LearningUnit[]>(`/learning-units?chapter_id=${selectedChapterId}`))
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao carregar unidades.')
    }
  }

  useEffect(() => {
    void loadUnits(chapterId)
    const chapter = chapters.find((item) => item.id === chapterId)
    if (chapter) {
      setForm((current) => ({
        ...current,
        startPage: String(chapter.start_page),
        endPage: String(chapter.end_page),
        position: '0',
      }))
    }
  }, [chapterId])

  function resetForm() {
    const chapter = chapters.find((item) => item.id === chapterId)
    setEditingId(null)
    setForm({
      ...initialForm,
      startPage: chapter ? String(chapter.start_page) : '',
      endPage: chapter ? String(chapter.end_page) : '',
      position: String(units.length),
    })
  }

  function editUnit(unit: LearningUnit) {
    setEditingId(unit.id)
    setForm({
      title: unit.title,
      subjectId: unit.subject_id ?? '',
      description: unit.description ?? '',
      startPage: unit.start_page?.toString() ?? '',
      endPage: unit.end_page?.toString() ?? '',
      schoolYear: unit.school_year ?? '',
      difficulty: unit.difficulty_level,
      disciplinaryObjective: unit.disciplinary_objective ?? '',
      isConfirmed: unit.is_confirmed,
      position: String(unit.position),
    })
  }

  async function saveUnit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!chapterId) {
      setError('Selecione um capítulo confirmado.')
      return
    }
    setBusy(true)
    setError('')
    setSuccess('')
    const unitPayload = {
      title: form.title.trim(),
      subject_id: form.subjectId || null,
      description: form.description.trim() || null,
      start_page: form.startPage ? Number(form.startPage) : null,
      end_page: form.endPage ? Number(form.endPage) : null,
      school_year: form.schoolYear.trim() || null,
      difficulty_level: form.difficulty,
      disciplinary_objective: form.disciplinaryObjective.trim() || null,
      is_confirmed: form.isConfirmed,
      position: Number(form.position),
    }
    try {
      if (editingId) {
        await api<LearningUnit>(`/learning-units/${editingId}`, {
          method: 'PATCH',
          body: JSON.stringify(unitPayload),
        })
        setSuccess('Unidade pedagógica atualizada.')
      } else {
        await api<LearningUnit>('/learning-units', {
          method: 'POST',
          body: JSON.stringify({ ...unitPayload, chapter_id: chapterId }),
        })
        setSuccess('Unidade pedagógica criada.')
      }
      resetForm()
      await loadUnits(chapterId)
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível salvar a unidade.',
      )
    } finally {
      setBusy(false)
    }
  }

  async function removeUnit(unit: LearningUnit) {
    if (!window.confirm(`Excluir a unidade “${unit.title}”?`)) return
    try {
      await api<void>(`/learning-units/${unit.id}`, { method: 'DELETE' })
      setSuccess('Unidade excluída.')
      await loadUnits(chapterId)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao excluir unidade.')
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <span className="eyebrow">CONTEÚDO PEDAGÓGICO</span>
          <h1>Unidades pedagógicas</h1>
          <p>
            Divida capítulos extensos em conceitos específicos, como frações equivalentes,
            ecossistemas ou interpretação textual, antes do chunking e do RAG.
          </p>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}

      <section className="panel">
        <div className="form-grid studio-two-columns">
          <label>
            Documento
            <select value={documentId} onChange={(event) => setDocumentId(event.target.value)}>
              <option value="">Selecione</option>
              {documents.map((document) => (
                <option key={document.id} value={document.id}>{document.original_filename}</option>
              ))}
            </select>
          </label>
          <label>
            Capítulo confirmado
            <select
              value={chapterId}
              onChange={(event) => setChapterId(event.target.value)}
              disabled={!documentId}
            >
              <option value="">Selecione</option>
              {chapters.map((chapter) => (
                <option key={chapter.id} value={chapter.id}>
                  {chapter.title} — páginas {chapter.start_page}–{chapter.end_page}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <div className="two-columns">
        {canWrite ? (
          <form className="panel form-grid" onSubmit={saveUnit}>
            <h2>{editingId ? 'Editar unidade' : 'Nova unidade'}</h2>
            <label>
              Título
              <input
                value={form.title}
                onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                placeholder="Ex.: Frações equivalentes"
                required
              />
            </label>
            <label>
              Disciplina
              <select
                value={form.subjectId}
                onChange={(event) => setForm((current) => ({ ...current, subjectId: event.target.value }))}
              >
                <option value="">Herdar do planejamento</option>
                {subjects.map((subject) => (
                  <option key={subject.id} value={subject.id}>{subject.name}</option>
                ))}
              </select>
            </label>
            <div className="form-grid studio-two-columns">
              <label>
                Página inicial
                <input
                  type="number"
                  min="1"
                  value={form.startPage}
                  onChange={(event) => setForm((current) => ({ ...current, startPage: event.target.value }))}
                />
              </label>
              <label>
                Página final
                <input
                  type="number"
                  min="1"
                  value={form.endPage}
                  onChange={(event) => setForm((current) => ({ ...current, endPage: event.target.value }))}
                />
              </label>
            </div>
            <label>
              Ano ou série
              <input
                value={form.schoolYear}
                onChange={(event) => setForm((current) => ({ ...current, schoolYear: event.target.value }))}
                placeholder="Ex.: 6º ano"
              />
            </label>
            <label>
              Dificuldade
              <select
                value={form.difficulty}
                onChange={(event) => setForm((current) => ({
                  ...current,
                  difficulty: event.target.value as DifficultyLevel,
                }))}
              >
                {(Object.keys(difficultyLabels) as DifficultyLevel[]).map((difficulty) => (
                  <option key={difficulty} value={difficulty}>{difficultyLabels[difficulty]}</option>
                ))}
              </select>
            </label>
            <label>
              Descrição
              <textarea
                rows={4}
                value={form.description}
                onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
              />
            </label>
            <label>
              Objetivo disciplinar
              <textarea
                rows={4}
                value={form.disciplinaryObjective}
                onChange={(event) => setForm((current) => ({ ...current, disciplinaryObjective: event.target.value }))}
              />
            </label>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={form.isConfirmed}
                onChange={(event) => setForm((current) => ({ ...current, isConfirmed: event.target.checked }))}
              />
              Confirmada para uso futuro no RAG
            </label>
            <button className="primary" disabled={busy || !chapterId} type="submit">
              {busy ? 'Salvando...' : editingId ? 'Atualizar unidade' : 'Criar unidade'}
            </button>
            {editingId ? <button type="button" onClick={resetForm}>Cancelar edição</button> : null}
          </form>
        ) : null}

        <section className="panel">
          <h2>Unidades do capítulo</h2>
          <div className="learning-unit-list">
            {units.map((unit) => (
              <article className={unit.is_confirmed ? 'learning-unit-card confirmed' : 'learning-unit-card'} key={unit.id}>
                <div className="project-card-heading">
                  <strong>{unit.title}</strong>
                  <span className={unit.is_confirmed ? 'publication-chip published' : 'publication-chip'}>
                    {unit.is_confirmed ? 'Confirmada' : 'Em revisão'}
                  </span>
                </div>
                <p>{unit.description || 'Sem descrição.'}</p>
                <small>
                  Páginas {unit.start_page ?? '—'}–{unit.end_page ?? '—'} • {difficultyLabels[unit.difficulty_level]}
                </small>
                {canWrite ? (
                  <div className="card-actions">
                    <button type="button" onClick={() => editUnit(unit)}>Editar</button>
                    <button className="danger-button" type="button" onClick={() => void removeUnit(unit)}>Excluir</button>
                  </div>
                ) : null}
              </article>
            ))}
            {chapterId && units.length === 0 ? <p>Nenhuma unidade criada para este capítulo.</p> : null}
            {!chapterId ? <p>Selecione um capítulo confirmado.</p> : null}
          </div>
        </section>
      </div>
    </section>
  )
}
