import { FormEvent, useEffect, useState } from 'react'

import { api } from '../lib/api'
import type {
  FeedbackRating,
  RetrievalIndexJob,
  SearchMode,
  SearchResponse,
  SearchResult,
} from '../types/retrieval'

const modeLabels: Record<SearchMode, string> = {
  hybrid: 'Híbrida',
  semantic: 'Semântica',
  text: 'Palavras-chave',
}

function score(value?: number | null) {
  return value == null ? '—' : value.toFixed(3)
}

export function RagLabPage() {
  const [jobs, setJobs] = useState<RetrievalIndexJob[]>([])
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<SearchMode>('hybrid')
  const [topK, setTopK] = useState(8)
  const [jobId, setJobId] = useState('')
  const [response, setResponse] = useState<SearchResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    void api<RetrievalIndexJob[]>('/retrieval/index-jobs?status=indexed')
      .then(setJobs)
      .catch((caughtError: unknown) => {
        setError(caughtError instanceof Error ? caughtError.message : 'Falha ao carregar fontes indexadas.')
      })
  }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setSuccess('')
    try {
      setResponse(await api<SearchResponse>('/retrieval/search', {
        method: 'POST',
        body: JSON.stringify({
          query: query.trim(),
          mode,
          top_k: topK,
          candidate_k: Math.max(30, topK * 4),
          index_job_id: jobId || null,
          confirmed_only: true,
        }),
      }))
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha na busca.')
    } finally {
      setBusy(false)
    }
  }

  async function rate(result: SearchResult, rating: FeedbackRating) {
    try {
      await api('/retrieval/feedback', {
        method: 'POST',
        body: JSON.stringify({
          chunk_id: result.chunk_id,
          query_text: query,
          search_mode: mode,
          rating,
          notes: null,
        }),
      })
      setSuccess('Avaliação registrada para aprimorar a qualidade da recuperação.')
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao registrar avaliação.')
    }
  }

  async function copyContext() {
    if (!response) return
    const text = response.ordered_context
      .map((item) => `[${item.citation_label}]\n${item.content}`)
      .join('\n\n')
    await navigator.clipboard.writeText(text)
    setSuccess('Contexto ordenado copiado.')
  }

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <span className="eyebrow">LABORATÓRIO DE RECUPERAÇÃO</span>
          <h1>Laboratório RAG</h1>
          <p>
            Compare busca semântica, textual e híbrida. Os resultados são ranqueados por
            relevância e reorganizados em uma segunda visão para preservar a sequência da fonte.
          </p>
        </div><a className="secondary-button" href="/ia?module=rag&action=draft_from_sources">Usar contexto na IA</a>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}

      <form className="panel" onSubmit={submit}>
        <div className="form-grid studio-three-columns">
          <label className="full-width">
            Consulta pedagógica
            <textarea rows={3} required minLength={2} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ex.: Como reconhecer frações equivalentes?" />
          </label>
          <label>
            Modo de busca
            <select value={mode} onChange={(event) => setMode(event.target.value as SearchMode)}>
              {Object.entries(modeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label>
            Fonte indexada
            <select value={jobId} onChange={(event) => setJobId(event.target.value)}>
              <option value="">Todas as fontes da organização</option>
              {jobs.map((job) => <option key={job.id} value={job.id}>{job.source_title}</option>)}
            </select>
          </label>
          <label>
            Quantidade de resultados
            <input type="number" min={1} max={30} value={topK} onChange={(event) => setTopK(Number(event.target.value))} />
          </label>
        </div>
        <button className="primary" disabled={busy || query.trim().length < 2} type="submit">
          {busy ? 'Pesquisando…' : 'Pesquisar conteúdo'}
        </button>
      </form>

      {response ? (
        <>
          <section className="panel">
            <div className="panel-title-row">
              <div>
                <span className="eyebrow">RANKING DE RELEVÂNCIA</span>
                <h2>{response.results.length} resultados</h2>
                <p>{response.total_candidates} candidatos analisados no modo {modeLabels[response.mode].toLowerCase()}.</p>
              </div>
            </div>
            <div className="search-result-list">
              {response.results.map((result, index) => (
                <article className="search-result-card" key={result.chunk_id}>
                  <header>
                    <span className="result-rank">#{index + 1}</span>
                    <div>
                      <strong>{result.heading ?? 'Trecho pedagógico'}</strong>
                      <small>{result.page_start ? `p. ${result.page_start}${result.page_end !== result.page_start ? `–${result.page_end}` : ''}` : 'fonte textual'}</small>
                    </div>
                  </header>
                  <p>{result.content}</p>
                  <div className="score-grid">
                    <span>Vetor <strong>{score(result.vector_score)}</strong></span>
                    <span>Texto <strong>{score(result.text_score)}</strong></span>
                    <span>Híbrido <strong>{score(result.hybrid_score)}</strong></span>
                  </div>
                  <small className="retrieval-explanation">{result.explanation}</small>
                  {result.security_flag ? <div className="alert error">Fonte não executável: possível instrução maliciosa.</div> : null}
                  <div className="feedback-actions">
                    <span>Este trecho é:</span>
                    <button type="button" onClick={() => void rate(result, 'relevant')}>Relevante</button>
                    <button type="button" onClick={() => void rate(result, 'partial')}>Parcial</button>
                    <button type="button" onClick={() => void rate(result, 'irrelevant')}>Irrelevante</button>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="panel-title-row">
              <div>
                <span className="eyebrow">CONTEXTO PARA A SPRINT 06</span>
                <h2>Trechos na ordem da fonte</h2>
                <p>A seleção relevante é reorganizada por página e posição, evitando conceitos e diálogos fora de sequência.</p>
              </div>
              <button type="button" onClick={() => void copyContext()}>Copiar contexto</button>
            </div>
            <ol className="ordered-context-list">
              {response.ordered_context.map((item) => (
                <li key={item.chunk_id}>
                  <strong>{item.citation_label}</strong>
                  <p>{item.content}</p>
                </li>
              ))}
            </ol>
          </section>
        </>
      ) : null}
    </section>
  )
}
