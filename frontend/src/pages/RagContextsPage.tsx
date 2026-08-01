import { FormEvent, useEffect, useMemo, useState } from 'react'

import { api } from '../lib/api'
import type { GenerationProject } from '../types/pedagogy'
import type { RetrievalIndexJob, SearchMode } from '../types/retrieval'
import type { RagContext, RagContextStatus, RagContextSummary } from '../types/rag'

const statusLabels: Record<RagContextStatus, string> = {
  draft: 'Rascunho',
  in_review: 'Em revisão',
  ready_with_warnings: 'Pronto com ressalvas',
  insufficient: 'Contexto insuficiente',
  conflicted: 'Fontes conflitantes',
  approved: 'Aprovado',
  archived: 'Arquivado',
}

function percentage(value: number) {
  return `${Math.round(value)}%`
}

export function RagContextsPage() {
  const [contexts, setContexts] = useState<RagContextSummary[]>([])
  const [projects, setProjects] = useState<GenerationProject[]>([])
  const [jobs, setJobs] = useState<RetrievalIndexJob[]>([])
  const [selected, setSelected] = useState<RagContext | null>(null)
  const [generationProjectId, setGenerationProjectId] = useState('')
  const [indexJobId, setIndexJobId] = useState('')
  const [title, setTitle] = useState('Contexto pedagógico')
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<SearchMode>('hybrid')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function load() {
    const [contextData, projectData, jobData] = await Promise.all([
      api<RagContextSummary[]>('/rag-contexts'),
      api<GenerationProject[]>('/generation-projects'),
      api<RetrievalIndexJob[]>('/retrieval/index-jobs'),
    ])
    setContexts(contextData)
    setProjects(projectData)
    setJobs(jobData.filter((job) => job.status === 'indexed'))
    if (!generationProjectId && projectData.length) setGenerationProjectId(projectData[0].id)
  }

  useEffect(() => {
    void load().catch((caughtError) => {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao carregar contextos.')
    })
  }, [])

  const latestEvaluation = useMemo(
    () => selected?.evaluations[selected.evaluations.length - 1],
    [selected],
  )

  async function assemble(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setSuccess('')
    try {
      const context = await api<RagContext>('/rag-contexts/assemble', {
        method: 'POST',
        body: JSON.stringify({
          generation_project_id: generationProjectId,
          title,
          query,
          search_mode: mode,
          top_k: 8,
          candidate_k: 30,
          index_job_id: indexJobId || null,
          include_suspicious_sources: false,
        }),
      })
      setSelected(context)
      setSuccess('Contexto montado com fatos, fontes, regras e avaliação de qualidade.')
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao montar contexto.')
    } finally {
      setBusy(false)
    }
  }

  async function openContext(contextId: string) {
    setError('')
    try {
      setSelected(await api<RagContext>(`/rag-contexts/${contextId}`))
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao abrir contexto.')
    }
  }

  async function reviewFact(factId: string, reviewStatus: 'approved' | 'rejected') {
    if (!selected) return
    await api(`/rag-contexts/${selected.id}/facts/${factId}`, {
      method: 'PATCH',
      body: JSON.stringify({ review_status: reviewStatus }),
    })
    await openContext(selected.id)
  }

  async function toggleSource(sourceId: string, isIncluded: boolean) {
    if (!selected) return
    await api(`/rag-contexts/${selected.id}/sources/${sourceId}`, {
      method: 'PATCH',
      body: JSON.stringify({ is_included: isIncluded }),
    })
    await openContext(selected.id)
  }

  async function approve() {
    if (!selected) return
    setError('')
    try {
      const context = await api<RagContext>(`/rag-contexts/${selected.id}/approve`, {
        method: 'POST',
      })
      setSelected(context)
      setSuccess('Contexto aprovado e pronto para o gerador da Sprint 07.')
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha na aprovação.')
    }
  }

  async function copyContract() {
    if (!selected) return
    await navigator.clipboard.writeText(selected.assembled_context_text)
    setSuccess('Contrato e contexto copiados.')
  }

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <span className="eyebrow">SPRINT 06</span>
          <h1>Construtor de Contexto RAG</h1>
          <p>
            Transforme os trechos recuperados em fatos citáveis, regras pedagógicas e liberdade
            narrativa controlada antes de gerar histórias, exercícios ou jogos.
          </p>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}

      <form className="panel" onSubmit={assemble}>
        <div className="form-grid studio-three-columns">
          <label>
            Planejamento pedagógico
            <select required value={generationProjectId} onChange={(event) => setGenerationProjectId(event.target.value)}>
              <option value="">Selecione</option>
              {projects.map((project) => <option value={project.id} key={project.id}>{project.title} · {project.topic}</option>)}
            </select>
          </label>
          <label>
            Fonte indexada
            <select value={indexJobId} onChange={(event) => setIndexJobId(event.target.value)}>
              <option value="">Todas as fontes indexadas</option>
              {jobs.map((job) => <option value={job.id} key={job.id}>{job.source_title}</option>)}
            </select>
          </label>
          <label>
            Modo de recuperação
            <select value={mode} onChange={(event) => setMode(event.target.value as SearchMode)}>
              <option value="hybrid">Híbrida</option>
              <option value="semantic">Semântica</option>
              <option value="text">Palavras-chave</option>
            </select>
          </label>
          <label className="full-width">
            Título do contexto
            <input required minLength={3} value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label className="full-width">
            O que o futuro material precisa ensinar?
            <textarea rows={4} required minLength={2} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ex.: Explique frações equivalentes, mostre um padrão e prepare uma situação narrativa adequada ao 6º ano." />
          </label>
        </div>
        <button className="primary" type="submit" disabled={busy || !generationProjectId || query.trim().length < 2}>
          {busy ? 'Montando contexto…' : 'Montar contexto verificável'}
        </button>
      </form>

      <section className="panel">
        <div className="panel-title-row">
          <div>
            <span className="eyebrow">HISTÓRICO</span>
            <h2>Contextos do projeto</h2>
          </div>
        </div>
        <div className="rag-context-grid">
          {contexts.map((context) => (
            <button className="rag-context-card" type="button" key={context.id} onClick={() => void openContext(context.id)}>
              <div>
                <strong>{context.title}</strong>
                <p>{context.query}</p>
              </div>
              <span className={`status-chip ${context.status.replaceAll('_', '-')}`}>{statusLabels[context.status]}</span>
              <small>Qualidade {percentage(context.quality_score)} · {context.source_count} fontes · v{context.context_version}</small>
            </button>
          ))}
          {!contexts.length ? <p>Nenhum contexto montado até agora.</p> : null}
        </div>
      </section>

      {selected ? (
        <>
          <section className="panel rag-context-hero">
            <div>
              <span className="eyebrow">CONTRATO PEDAGÓGICO-NARRATIVO</span>
              <h2>{selected.title}</h2>
              <p>{selected.readiness_reason}</p>
              <div className="score-grid">
                <span>Qualidade <strong>{percentage(selected.quality_score)}</strong></span>
                <span>Fontes <strong>{selected.sources.filter((source) => source.is_included).length}</strong></span>
                <span>Fatos <strong>{selected.facts.length}</strong></span>
                <span>Tokens estimados <strong>{selected.token_estimate}</strong></span>
              </div>
            </div>
            <div className="rag-context-actions">
              <span className={`status-chip ${selected.status.replaceAll('_', '-')}`}>{statusLabels[selected.status]}</span>
              <button type="button" onClick={() => void copyContract()}>Copiar contrato</button>
              <button className="primary" type="button" disabled={selected.status === 'approved'} onClick={() => void approve()}>Aprovar contexto</button>
            </div>
          </section>

          {latestEvaluation ? (
            <section className="panel">
              <span className="eyebrow">QUALIDADE DO CONTEXTO</span>
              <div className="quality-score-grid">
                <div><strong>{percentage(latestEvaluation.relevance_score)}</strong><span>Relevância</span></div>
                <div><strong>{percentage(latestEvaluation.coverage_score)}</strong><span>Cobertura</span></div>
                <div><strong>{percentage(latestEvaluation.diversity_score)}</strong><span>Diversidade</span></div>
                <div><strong>{percentage(latestEvaluation.traceability_score)}</strong><span>Rastreabilidade</span></div>
                <div><strong>{percentage(latestEvaluation.consistency_score)}</strong><span>Consistência</span></div>
                <div><strong>{percentage(latestEvaluation.safety_score)}</strong><span>Segurança</span></div>
              </div>
            </section>
          ) : null}

          <section className="panel">
            <span className="eyebrow">FATOS OBRIGATÓRIOS</span>
            <h2>Revisão docente</h2>
            <div className="rag-fact-list">
              {selected.facts.map((fact) => (
                <article key={fact.id} className={`rag-fact-card ${fact.review_status}`}>
                  <div>
                    <strong>{fact.fact_type}</strong>
                    <p>{fact.statement}</p>
                    <small>{fact.citation_codes.join(', ')} · confiança {percentage(fact.confidence * 100)}</small>
                  </div>
                  <div className="feedback-actions">
                    <button type="button" onClick={() => void reviewFact(fact.id, 'approved')}>Aprovar</button>
                    <button type="button" onClick={() => void reviewFact(fact.id, 'rejected')}>Rejeitar</button>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="panel">
            <span className="eyebrow">RASTREABILIDADE</span>
            <h2>Fontes e páginas</h2>
            <div className="rag-source-list">
              {selected.sources.map((source) => (
                <article key={source.id} className={`rag-source-card ${source.safety_status}`}>
                  <header>
                    <strong>{source.citation_code} · {source.citation_label}</strong>
                    <label className="inline-check"><input type="checkbox" checked={source.is_included} onChange={(event) => void toggleSource(source.id, event.target.checked)} /> Incluir</label>
                  </header>
                  <p>{source.content_snapshot}</p>
                  <small>{source.inclusion_reason}</small>
                </article>
              ))}
            </div>
          </section>

          <section className="panel">
            <span className="eyebrow">REGRAS</span>
            <h2>Coerência com liberdade criativa</h2>
            <div className="rag-rule-list">
              {selected.rules.map((rule) => (
                <article key={rule.id}>
                  <strong>{rule.category} · {rule.priority}</strong>
                  <p>{rule.rule_text}</p>
                </article>
              ))}
            </div>
          </section>

          {selected.conflicts.length ? (
            <section className="panel">
              <span className="eyebrow">CONFLITOS</span>
              <h2>Revisão necessária</h2>
              {selected.conflicts.map((conflict) => (
                <article className="alert error" key={conflict.id}>
                  <strong>{conflict.description}</strong>
                  <p>A: {conflict.statement_a}</p>
                  <p>B: {conflict.statement_b}</p>
                </article>
              ))}
            </section>
          ) : null}

          <section className="panel">
            <div className="panel-title-row">
              <div>
                <span className="eyebrow">SAÍDA PARA A SPRINT 07</span>
                <h2>Contexto protegido</h2>
              </div>
            </div>
            <pre className="rag-contract-preview">{selected.assembled_context_text}</pre>
          </section>
        </>
      ) : null}
    </section>
  )
}
