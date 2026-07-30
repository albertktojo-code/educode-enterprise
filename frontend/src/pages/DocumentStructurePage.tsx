import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import type {
  ChapterTextPreview,
  DocumentChapter,
  DocumentDetail,
  DocumentPageDetail,
  DocumentPageItem,
  DocumentStructureSummary,
} from '../types/document'

const pageKindLabels = {
  textual: 'Textual',
  scanned: 'Escaneada',
  mixed: 'Mista',
  empty: 'Vazia',
} as const

const methodLabels = {
  pdf_toc: 'Sumário do PDF',
  automatic_heading: 'Detecção automática',
  manual: 'Manual',
} as const

interface ChapterFormState {
  title: string
  chapterNumber: string
  startPage: string
  endPage: string
  summary: string
  isConfirmed: boolean
  position: string
}

const emptyChapterForm: ChapterFormState = {
  title: '',
  chapterNumber: '',
  startPage: '1',
  endPage: '1',
  summary: '',
  isConfirmed: false,
  position: '0',
}

export function DocumentStructurePage() {
  const { documentId } = useParams()
  const { user } = useAuth()
  const role = user?.memberships[0]?.role
  const canWrite = ['owner', 'admin', 'teacher'].includes(role ?? '')

  const [document, setDocument] = useState<DocumentDetail | null>(null)
  const [summary, setSummary] = useState<DocumentStructureSummary | null>(null)
  const [pages, setPages] = useState<DocumentPageItem[]>([])
  const [chapters, setChapters] = useState<DocumentChapter[]>([])
  const [selectedPage, setSelectedPage] = useState<DocumentPageDetail | null>(null)
  const [chapterPreview, setChapterPreview] = useState<ChapterTextPreview | null>(null)
  const [editingChapterId, setEditingChapterId] = useState<string | null>(null)
  const [chapterForm, setChapterForm] = useState<ChapterFormState>(emptyChapterForm)
  const [busy, setBusy] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function loadStructure() {
    if (!documentId) return
    setError('')
    try {
      const [documentData, summaryData, pageData, chapterData] = await Promise.all([
        api<DocumentDetail>(`/documents/${documentId}`),
        api<DocumentStructureSummary>(`/documents/${documentId}/structure-summary`),
        api<DocumentPageItem[]>(`/documents/${documentId}/pages`),
        api<DocumentChapter[]>(`/documents/${documentId}/chapters`),
      ])
      setDocument(documentData)
      setSummary(summaryData)
      setPages(pageData)
      setChapters(chapterData)
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível carregar a estrutura documental.',
      )
    }
  }

  useEffect(() => {
    void loadStructure()
  }, [documentId])

  const confirmedPercentage = useMemo(() => {
    if (!summary?.chapter_count) return 0
    return Math.round((summary.confirmed_chapters / summary.chapter_count) * 100)
  }, [summary])

  function resetForm() {
    setEditingChapterId(null)
    setChapterForm({
      ...emptyChapterForm,
      endPage: String(document?.page_count ?? 1),
      position: String(chapters.length),
    })
  }

  function editChapter(chapter: DocumentChapter) {
    setEditingChapterId(chapter.id)
    setChapterForm({
      title: chapter.title,
      chapterNumber: chapter.chapter_number?.toString() ?? '',
      startPage: String(chapter.start_page),
      endPage: String(chapter.end_page),
      summary: chapter.summary ?? '',
      isConfirmed: chapter.is_confirmed,
      position: String(chapter.position),
    })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function saveChapter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!documentId) return

    setBusy(true)
    setError('')
    setSuccess('')
    const payload = {
      title: chapterForm.title.trim(),
      chapter_number: chapterForm.chapterNumber
        ? Number(chapterForm.chapterNumber)
        : null,
      start_page: Number(chapterForm.startPage),
      end_page: Number(chapterForm.endPage),
      summary: chapterForm.summary.trim() || null,
      is_confirmed: chapterForm.isConfirmed,
      position: Number(chapterForm.position),
    }

    try {
      if (editingChapterId) {
        await api<DocumentChapter>(
          `/documents/${documentId}/chapters/${editingChapterId}`,
          {
            method: 'PATCH',
            body: JSON.stringify(payload),
          },
        )
        setSuccess('Capítulo atualizado.')
      } else {
        await api<DocumentChapter>(`/documents/${documentId}/chapters`, {
          method: 'POST',
          body: JSON.stringify(payload),
        })
        setSuccess('Capítulo manual criado.')
      }
      resetForm()
      await loadStructure()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível salvar o capítulo.',
      )
    } finally {
      setBusy(false)
    }
  }

  async function toggleConfirmation(chapter: DocumentChapter) {
    if (!documentId) return
    setBusyId(chapter.id)
    setError('')
    setSuccess('')
    try {
      await api<DocumentChapter>(
        `/documents/${documentId}/chapters/${chapter.id}`,
        {
          method: 'PATCH',
          body: JSON.stringify({ is_confirmed: !chapter.is_confirmed }),
        },
      )
      setSuccess(
        chapter.is_confirmed
          ? 'Capítulo reaberto para revisão.'
          : 'Capítulo confirmado para uso futuro no RAG.',
      )
      await loadStructure()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível atualizar a confirmação.',
      )
    } finally {
      setBusyId(null)
    }
  }

  async function removeChapter(chapter: DocumentChapter) {
    if (!documentId) return
    if (!window.confirm(`Excluir o capítulo “${chapter.title}”?`)) return

    setBusyId(chapter.id)
    setError('')
    try {
      await api<void>(`/documents/${documentId}/chapters/${chapter.id}`, {
        method: 'DELETE',
      })
      if (editingChapterId === chapter.id) resetForm()
      if (chapterPreview?.chapter.id === chapter.id) setChapterPreview(null)
      setSuccess('Capítulo excluído.')
      await loadStructure()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível excluir o capítulo.',
      )
    } finally {
      setBusyId(null)
    }
  }

  async function detectAgain(replaceAll: boolean) {
    if (!documentId) return
    if (
      replaceAll &&
      !window.confirm(
        'Esta ação substituirá inclusive capítulos manuais e confirmados. Continuar?',
      )
    ) {
      return
    }

    setBusy(true)
    setError('')
    setSuccess('')
    try {
      await api<DocumentChapter[]>(`/documents/${documentId}/chapters/detect`, {
        method: 'POST',
        body: JSON.stringify({ replace_all: replaceAll }),
      })
      setSuccess(
        replaceAll
          ? 'A estrutura foi refeita automaticamente.'
          : 'Capítulos automáticos não confirmados foram detectados novamente.',
      )
      await loadStructure()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível detectar os capítulos.',
      )
    } finally {
      setBusy(false)
    }
  }

  async function reprocessDocument() {
    if (!documentId) return
    setBusy(true)
    setError('')
    setSuccess('')
    try {
      await api<DocumentDetail>(`/documents/${documentId}/process`, {
        method: 'POST',
      })
      setSuccess('Páginas reprocessadas. Capítulos confirmados e manuais foram preservados.')
      await loadStructure()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível reprocessar o documento.',
      )
    } finally {
      setBusy(false)
    }
  }

  async function openPage(pageNumber: number) {
    if (!documentId) return
    setBusyId(`page-${pageNumber}`)
    setError('')
    try {
      setSelectedPage(
        await api<DocumentPageDetail>(
          `/documents/${documentId}/pages/${pageNumber}`,
        ),
      )
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível abrir a página.',
      )
    } finally {
      setBusyId(null)
    }
  }

  async function openChapter(chapter: DocumentChapter) {
    if (!documentId) return
    setBusyId(chapter.id)
    setError('')
    try {
      setChapterPreview(
        await api<ChapterTextPreview>(
          `/documents/${documentId}/chapters/${chapter.id}/text`,
        ),
      )
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível abrir o conteúdo do capítulo.',
      )
    } finally {
      setBusyId(null)
    }
  }

  if (!documentId) {
    return <div className="alert error">Documento inválido.</div>
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <span className="eyebrow">ESTRUTURA DOCUMENTAL</span>
          <h1>{document?.original_filename ?? 'Carregando documento...'}</h1>
          <p>
            Revise páginas e capítulos antes de utilizar o conteúdo na busca
            semântica e nos futuros geradores de HQ, quiz, jogos e anime.
          </p>
        </div>
        <div className="header-actions">
          <Link className="secondary-button button-link" to="/documentos">
            Voltar aos documentos
          </Link>
          <Link className="secondary-button button-link" to="/unidades-pedagogicas">
            Criar unidades pedagógicas
          </Link>
          {canWrite ? (
            <button disabled={busy} onClick={() => void reprocessDocument()}>
              Reprocessar páginas
            </button>
          ) : null}
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}

      <div className="stats stats-five structure-stats">
        <article className="status-card">
          <span>Páginas</span>
          <strong>{summary?.page_count ?? 0}</strong>
          <small>{summary?.extracted_pages ?? 0} estruturadas</small>
        </article>
        <article className="status-card">
          <span>Capítulos</span>
          <strong>{summary?.chapter_count ?? 0}</strong>
          <small>{summary?.confirmed_chapters ?? 0} confirmados</small>
        </article>
        <article className="status-card">
          <span>Revisão</span>
          <strong>{confirmedPercentage}%</strong>
          <small>estrutura confirmada</small>
        </article>
        <article className="status-card">
          <span>OCR necessário</span>
          <strong>{summary?.ocr_required_pages ?? 0}</strong>
          <small>páginas escaneadas ou mistas</small>
        </article>
        <article className="status-card">
          <span>Texto nativo</span>
          <strong>{summary?.textual_pages ?? 0}</strong>
          <small>páginas textuais</small>
        </article>
      </div>

      <div className="dashboard-grid wide-left structure-editor-grid">
        <section className="panel">
          <div className="panel-title-row">
            <div>
              <h2>Capítulos detectados</h2>
              <p>
                Confirme apenas os intervalos corretos. Capítulos confirmados
                serão a fronteira de conteúdo para o RAG.
              </p>
            </div>
            {canWrite ? (
              <div className="card-actions compact">
                <button disabled={busy} onClick={() => void detectAgain(false)}>
                  Detectar novamente
                </button>
                <button
                  className="danger-button"
                  disabled={busy}
                  onClick={() => void detectAgain(true)}
                >
                  Refazer tudo
                </button>
              </div>
            ) : null}
          </div>

          {chapters.length === 0 ? (
            <p>Nenhum capítulo detectado. Processe o PDF ou crie um capítulo manual.</p>
          ) : (
            <div className="chapter-list">
              {chapters.map((chapter) => (
                <article
                  className={
                    chapter.is_confirmed
                      ? 'chapter-card confirmed'
                      : 'chapter-card'
                  }
                  key={chapter.id}
                >
                  <div className="chapter-card-main">
                    <div className="title-with-status">
                      <strong>{chapter.title}</strong>
                      <span
                        className={
                          chapter.is_confirmed
                            ? 'chapter-status confirmed'
                            : 'chapter-status review'
                        }
                      >
                        {chapter.is_confirmed ? 'Confirmado' : 'Revisar'}
                      </span>
                    </div>
                    <p>
                      Páginas {chapter.start_page}–{chapter.end_page} ·{' '}
                      {methodLabels[chapter.detection_method]}
                    </p>
                    <small>
                      Confiança automática: {Math.round(chapter.confidence * 100)}%
                    </small>
                    {chapter.summary ? <p>{chapter.summary}</p> : null}
                  </div>
                  <div className="card-actions compact">
                    <button
                      disabled={busyId === chapter.id}
                      onClick={() => void openChapter(chapter)}
                    >
                      Ver conteúdo
                    </button>
                    {canWrite ? (
                      <>
                        <button onClick={() => editChapter(chapter)}>Editar</button>
                        <button
                          disabled={busyId === chapter.id}
                          onClick={() => void toggleConfirmation(chapter)}
                        >
                          {chapter.is_confirmed ? 'Reabrir' : 'Confirmar'}
                        </button>
                        <button
                          className="danger-button"
                          disabled={busyId === chapter.id}
                          onClick={() => void removeChapter(chapter)}
                        >
                          Excluir
                        </button>
                      </>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        {canWrite ? (
          <form className="panel form-grid sticky-panel" onSubmit={saveChapter}>
            <div className="panel-title-row">
              <div>
                <h2>{editingChapterId ? 'Editar capítulo' : 'Novo capítulo'}</h2>
                <p>Use esta opção quando a detecção automática precisar de correção.</p>
              </div>
              {editingChapterId ? (
                <button className="text-button" type="button" onClick={resetForm}>
                  Cancelar
                </button>
              ) : null}
            </div>
            <label>
              Título
              <input
                value={chapterForm.title}
                onChange={(event) =>
                  setChapterForm((current) => ({
                    ...current,
                    title: event.target.value,
                  }))
                }
                required
              />
            </label>
            <div className="form-row-three">
              <label>
                Número
                <input
                  min="1"
                  type="number"
                  value={chapterForm.chapterNumber}
                  onChange={(event) =>
                    setChapterForm((current) => ({
                      ...current,
                      chapterNumber: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Página inicial
                <input
                  min="1"
                  max={document?.page_count ?? undefined}
                  type="number"
                  value={chapterForm.startPage}
                  onChange={(event) =>
                    setChapterForm((current) => ({
                      ...current,
                      startPage: event.target.value,
                    }))
                  }
                  required
                />
              </label>
              <label>
                Página final
                <input
                  min="1"
                  max={document?.page_count ?? undefined}
                  type="number"
                  value={chapterForm.endPage}
                  onChange={(event) =>
                    setChapterForm((current) => ({
                      ...current,
                      endPage: event.target.value,
                    }))
                  }
                  required
                />
              </label>
            </div>
            <label>
              Resumo ou observação do professor
              <textarea
                rows={5}
                value={chapterForm.summary}
                onChange={(event) =>
                  setChapterForm((current) => ({
                    ...current,
                    summary: event.target.value,
                  }))
                }
              />
            </label>
            <label>
              Posição
              <input
                min="0"
                type="number"
                value={chapterForm.position}
                onChange={(event) =>
                  setChapterForm((current) => ({
                    ...current,
                    position: event.target.value,
                  }))
                }
              />
            </label>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={chapterForm.isConfirmed}
                onChange={(event) =>
                  setChapterForm((current) => ({
                    ...current,
                    isConfirmed: event.target.checked,
                  }))
                }
              />
              Confirmar imediatamente para o futuro RAG
            </label>
            <button className="primary" disabled={busy}>
              {busy
                ? 'Salvando...'
                : editingChapterId
                  ? 'Salvar alterações'
                  : 'Criar capítulo'}
            </button>
          </form>
        ) : (
          <aside className="panel permission-panel">
            <h2>Revisão protegida</h2>
            <p>Seu papel permite consultar, mas não alterar a estrutura documental.</p>
          </aside>
        )}
      </div>

      <section className="panel page-structure-panel">
        <div className="panel-title-row">
          <div>
            <h2>Páginas extraídas</h2>
            <p>
              A classificação prepara o sistema para aplicar OCR somente quando
              necessário. O OCR será conectado em uma etapa posterior.
            </p>
          </div>
          <div className="page-legend">
            <span className="page-kind textual">Textual</span>
            <span className="page-kind mixed">Mista</span>
            <span className="page-kind scanned">Escaneada</span>
            <span className="page-kind empty">Vazia</span>
          </div>
        </div>

        {pages.length === 0 ? (
          <p>As páginas ainda não foram extraídas.</p>
        ) : (
          <div className="page-list">
            {pages.map((page) => (
              <article className="page-card" key={page.id}>
                <div className="page-number">{page.page_number}</div>
                <div className="page-card-main">
                  <div className="title-with-status">
                    <strong>Página {page.page_number}</strong>
                    <span className={`page-kind ${page.page_kind}`}>
                      {pageKindLabels[page.page_kind]}
                    </span>
                    {page.ocr_status === 'required' ? (
                      <span className="ocr-badge">OCR necessário</span>
                    ) : null}
                  </div>
                  <p>
                    {page.character_count} caracteres · {page.image_count} imagem(ns) ·{' '}
                    extração {page.extraction_method}
                  </p>
                  <small>{page.text_preview || 'Nenhum texto nativo encontrado.'}</small>
                </div>
                <button
                  disabled={busyId === `page-${page.page_number}`}
                  onClick={() => void openPage(page.page_number)}
                >
                  Abrir página
                </button>
              </article>
            ))}
          </div>
        )}
      </section>

      {chapterPreview ? (
        <section className="panel document-preview-panel">
          <div className="panel-title-row">
            <div>
              <h2>{chapterPreview.chapter.title}</h2>
              <p>
                Fontes: páginas {chapterPreview.source_pages.join(', ')} ·{' '}
                {chapterPreview.character_count} caracteres
              </p>
            </div>
            <button className="text-button" onClick={() => setChapterPreview(null)}>
              Fechar
            </button>
          </div>
          <pre className="extracted-text">{chapterPreview.text || 'Sem texto nativo.'}</pre>
        </section>
      ) : null}

      {selectedPage ? (
        <section className="panel document-preview-panel">
          <div className="panel-title-row">
            <div>
              <h2>Página {selectedPage.page_number}</h2>
              <p>
                {pageKindLabels[selectedPage.page_kind]} ·{' '}
                {selectedPage.character_count} caracteres
              </p>
            </div>
            <button className="text-button" onClick={() => setSelectedPage(null)}>
              Fechar
            </button>
          </div>
          {selectedPage.ocr_status === 'required' ? (
            <div className="alert warning">
              Esta página precisa de OCR para recuperar todo o conteúdo visual.
            </div>
          ) : null}
          <pre className="extracted-text">{selectedPage.text || 'Sem texto nativo.'}</pre>
        </section>
      ) : null}
    </section>
  )
}
