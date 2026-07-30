import { useEffect, useMemo, useState } from 'react'

import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import type { GenerationProject, GenerationSource, LearningUnit } from '../types/pedagogy'
import type {
  RetrievalChunk,
  RetrievalIndexJob,
  RetrievalStats,
} from '../types/retrieval'

const statusLabels: Record<RetrievalIndexJob['status'], string> = {
  not_indexed: 'Não indexado',
  processing: 'Processando',
  indexed: 'Indexado',
  stale: 'Desatualizado',
  failed: 'Falhou',
}

export function IndexingPage() {
  const { user } = useAuth()
  const role = user?.memberships[0]?.role
  const canWrite = ['owner', 'admin', 'teacher'].includes(role ?? '')
  const [units, setUnits] = useState<LearningUnit[]>([])
  const [generationProjects, setGenerationProjects] = useState<GenerationProject[]>([])
  const [jobs, setJobs] = useState<RetrievalIndexJob[]>([])
  const [stats, setStats] = useState<RetrievalStats | null>(null)
  const [selectedJob, setSelectedJob] = useState<RetrievalIndexJob | null>(null)
  const [chunks, setChunks] = useState<RetrievalChunk[]>([])
  const [targetChars, setTargetChars] = useState(1000)
  const [overlapChars, setOverlapChars] = useState(160)
  const [minChars, setMinChars] = useState(200)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function loadData() {
    const [unitData, projectData, jobData, statData] = await Promise.all([
      api<LearningUnit[]>('/learning-units'),
      api<GenerationProject[]>('/generation-projects'),
      api<RetrievalIndexJob[]>('/retrieval/index-jobs'),
      api<RetrievalStats>('/retrieval/stats'),
    ])
    setUnits(unitData.filter((unit) => unit.is_confirmed))
    setGenerationProjects(projectData)
    setJobs(jobData)
    setStats(statData)
  }

  useEffect(() => {
    void loadData().catch((caughtError: unknown) => {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao carregar a indexação.')
    })
  }, [])

  const jobsByUnit = useMemo(
    () => new Map(jobs.filter((job) => job.learning_unit_id).map((job) => [job.learning_unit_id, job])),
    [jobs],
  )
  const jobsByGenerationSource = useMemo(
    () => new Map(jobs.filter((job) => job.generation_source_id).map((job) => [job.generation_source_id, job])),
    [jobs],
  )
  const teacherSources = useMemo(
    () => generationProjects.flatMap((project) => project.sources
      .filter((source) => Boolean(source.content_text?.trim() || source.instructions?.trim()))
      .map((source) => ({ project, source }))),
    [generationProjects],
  )

  async function indexGenerationSource(project: GenerationProject, source: GenerationSource) {
    setBusyId(source.id)
    setError('')
    setSuccess('')
    try {
      await api<RetrievalIndexJob>(`/retrieval/index-generation-source/${source.id}`, {
        method: 'POST',
        body: JSON.stringify({
          target_chars: targetChars,
          overlap_chars: overlapChars,
          min_chars: minChars,
        }),
      })
      setSuccess(`A fonte textual de “${project.title}” foi indexada.`)
      await loadData()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao indexar a fonte textual.')
    } finally {
      setBusyId(null)
    }
  }

  async function indexUnit(unit: LearningUnit) {
    setBusyId(unit.id)
    setError('')
    setSuccess('')
    try {
      await api<RetrievalIndexJob>(`/retrieval/index-learning-unit/${unit.id}`, {
        method: 'POST',
        body: JSON.stringify({
          target_chars: targetChars,
          overlap_chars: overlapChars,
          min_chars: minChars,
        }),
      })
      setSuccess(`A unidade “${unit.title}” foi indexada com sucesso.`)
      await loadData()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao indexar a unidade.')
    } finally {
      setBusyId(null)
    }
  }

  async function inspectJob(job: RetrievalIndexJob) {
    setSelectedJob(job)
    setError('')
    try {
      setChunks(await api<RetrievalChunk[]>(`/retrieval/chunks?index_job_id=${job.id}`))
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao carregar os chunks.')
    }
  }

  async function removeIndex(job: RetrievalIndexJob) {
    if (!window.confirm(`Remover os chunks ativos de “${job.source_title}”? O documento original será preservado.`)) return
    try {
      await api<void>(`/retrieval/index-jobs/${job.id}/chunks`, { method: 'DELETE' })
      setSelectedJob(null)
      setChunks([])
      setSuccess('Índice removido sem apagar a fonte original.')
      await loadData()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao remover o índice.')
    }
  }

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <span className="eyebrow">SPRINT 05 · RECUPERAÇÃO</span>
          <h1>Indexação pedagógica</h1>
          <p>
            Crie chunks hierárquicos por unidade confirmada, preservando capítulo, páginas,
            ordem da fonte e rastreabilidade para o contexto RAG.
          </p>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}

      <div className="stats-grid retrieval-stats">
        <article className="stat-card"><span>Fontes indexadas</span><strong>{stats?.indexed_jobs ?? 0}</strong></article>
        <article className="stat-card"><span>Chunks ativos</span><strong>{stats?.active_chunks ?? 0}</strong></article>
        <article className="stat-card"><span>Desatualizados</span><strong>{stats?.stale_jobs ?? 0}</strong></article>
        <article className="stat-card"><span>Alertas de segurança</span><strong>{stats?.flagged_chunks ?? 0}</strong></article>
      </div>

      <section className="panel">
        <div className="panel-title-row">
          <div>
            <h2>Perfil de chunking</h2>
            <p>Configuração determinística aplicada às próximas indexações e reindexações.</p>
          </div>
          <span className="role-chip">hierarchical-v1</span>
        </div>
        <div className="form-grid studio-three-columns">
          <label>
            Tamanho-alvo
            <input type="number" min={300} max={4000} value={targetChars} onChange={(event) => setTargetChars(Number(event.target.value))} />
          </label>
          <label>
            Sobreposição
            <input type="number" min={0} max={800} value={overlapChars} onChange={(event) => setOverlapChars(Number(event.target.value))} />
          </label>
          <label>
            Tamanho mínimo
            <input type="number" min={50} max={1200} value={minChars} onChange={(event) => setMinChars(Number(event.target.value))} />
          </label>
        </div>
      </section>

      <section className="panel">
        <div className="panel-title-row">
          <div>
            <h2>Unidades confirmadas</h2>
            <p>Somente unidades e capítulos confirmados podem ser indexados por padrão.</p>
          </div>
        </div>
        <div className="retrieval-source-list">
          {units.length === 0 ? <p className="muted">Nenhuma unidade confirmada disponível.</p> : null}
          {units.map((unit) => {
            const job = jobsByUnit.get(unit.id)
            return (
              <article className="retrieval-source-row" key={unit.id}>
                <div>
                  <strong>{unit.title}</strong>
                  <p>{unit.disciplinary_objective ?? unit.description ?? 'Sem objetivo informado.'}</p>
                  <small>
                    {unit.start_page && unit.end_page ? `Páginas ${unit.start_page}–${unit.end_page}` : 'Faixa de páginas herdada do capítulo'}
                  </small>
                </div>
                <div className="retrieval-row-status">
                  <span className={`status-chip ${job?.status ?? 'not-indexed'}`}>
                    {job ? statusLabels[job.status] : 'Não indexada'}
                  </span>
                  {job ? <small>{job.active_chunk_count} chunks · revisão {job.indexing_revision}</small> : null}
                </div>
                <div className="card-actions">
                  {job ? <button type="button" onClick={() => void inspectJob(job)}>Ver chunks</button> : null}
                  {canWrite ? (
                    <button className="primary" disabled={busyId === unit.id} type="button" onClick={() => void indexUnit(unit)}>
                      {busyId === unit.id ? 'Indexando…' : job ? 'Reindexar' : 'Indexar'}
                    </button>
                  ) : null}
                  {canWrite && job?.active_chunk_count ? (
                    <button className="danger-button" type="button" onClick={() => void removeIndex(job)}>Remover índice</button>
                  ) : null}
                </div>
              </article>
            )
          })}
        </div>
      </section>

      <section className="panel">
        <div className="panel-title-row">
          <div>
            <h2>Textos e instruções do professor</h2>
            <p>Fontes dos projetos pedagógicos também podem participar da recuperação híbrida.</p>
          </div>
        </div>
        <div className="retrieval-source-list">
          {teacherSources.length === 0 ? <p className="muted">Nenhuma fonte textual de projeto disponível.</p> : null}
          {teacherSources.map(({ project, source }) => {
            const job = jobsByGenerationSource.get(source.id)
            return (
              <article className="retrieval-source-row" key={source.id}>
                <div>
                  <strong>{project.title}</strong>
                  <p>{source.content_text?.slice(0, 220) || source.instructions?.slice(0, 220)}</p>
                  <small>{source.source_type} · prioridade {source.priority} · peso {source.weight}</small>
                </div>
                <div className="retrieval-row-status">
                  <span className={`status-chip ${job?.status ?? 'not-indexed'}`}>
                    {job ? statusLabels[job.status] : 'Não indexada'}
                  </span>
                  {job ? <small>{job.active_chunk_count} chunks · revisão {job.indexing_revision}</small> : null}
                </div>
                <div className="card-actions">
                  {job ? <button type="button" onClick={() => void inspectJob(job)}>Ver chunks</button> : null}
                  {canWrite ? (
                    <button className="primary" disabled={busyId === source.id} type="button" onClick={() => void indexGenerationSource(project, source)}>
                      {busyId === source.id ? 'Indexando…' : job ? 'Reindexar' : 'Indexar'}
                    </button>
                  ) : null}
                  {canWrite && job?.active_chunk_count ? (
                    <button className="danger-button" type="button" onClick={() => void removeIndex(job)}>Remover índice</button>
                  ) : null}
                </div>
              </article>
            )
          })}
        </div>
      </section>

      {selectedJob ? (
        <section className="panel">
          <div className="panel-title-row">
            <div>
              <span className="eyebrow">INSPEÇÃO DA FONTE</span>
              <h2>{selectedJob.source_title}</h2>
              <p>{selectedJob.embedding_model} · {selectedJob.embedding_dimension} dimensões</p>
            </div>
            <button type="button" onClick={() => { setSelectedJob(null); setChunks([]) }}>Fechar</button>
          </div>
          <div className="chunk-list">
            {chunks.map((chunk) => (
              <article className="chunk-card" key={chunk.id}>
                <header>
                  <strong>Trecho {chunk.chunk_index + 1}</strong>
                  <span>{chunk.page_start ? `p. ${chunk.page_start}${chunk.page_end !== chunk.page_start ? `–${chunk.page_end}` : ''}` : 'fonte textual'}</span>
                  <small>{chunk.character_count} caracteres · ~{chunk.token_estimate} tokens</small>
                </header>
                <p>{chunk.content}</p>
                {chunk.security_flag ? <div className="alert error">{chunk.security_notes}</div> : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </section>
  )
}
