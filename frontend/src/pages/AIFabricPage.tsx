import { FormEvent, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { api } from '../lib/api'

type Capability = {
  module_name: string
  actions: string[]
  human_approval_required: boolean
  enabled: boolean
  notes: string
}

type AIResult = {
  id: string
  result_type: string
  structured_content: Record<string, unknown>
  text_content: string
  review_status: string
  applied_to_module: boolean
  validation_results: { valid?: boolean; warnings?: string[] }
  safety_results: { safe?: boolean; provider_mode?: string }
}

type AIRequest = {
  id: string
  flow_id: string
  module_name: string
  action_name: string
  status: string
  estimated_cost: number
  error_message: string
  source_snapshot: { citations?: Array<{ code: string; label: string }> }
  results: AIResult[]
  created_at: string
}

const moduleLabels: Record<string, string> = {
  planning: 'Planejamento pedagógico',
  rag: 'Fontes e RAG',
  comics: 'HQs e narrativas',
  assets: 'Biblioteca de elementos',
  assessments: 'Avaliações',
  grading: 'Correção assistida',
  analytics: 'Learning Analytics',
  interventions: 'Intervenções',
  statistics: 'Laboratório estatístico',
  reports: 'Relatórios',
  accessibility: 'Acessibilidade',
}

export function AIFabricPage() {
  const [searchParams] = useSearchParams()
  const [capabilities, setCapabilities] = useState<Capability[]>([])
  const [requests, setRequests] = useState<AIRequest[]>([])
  const [moduleName, setModuleName] = useState(searchParams.get('module') ?? 'planning')
  const [actionName, setActionName] = useState(searchParams.get('action') ?? 'generate_lesson_plan')
  const [topic, setTopic] = useState('Pensamento Computacional com HQs')
  const [contextJson, setContextJson] = useState('{\n  "year_level": "6º ano",\n  "curriculum_skill_codes": [],\n  "ct_pillar_codes": ["decomposition", "algorithms"]\n}')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    const [capabilityRows, requestRows] = await Promise.all([
      api<Capability[]>('/ai/capabilities'),
      api<AIRequest[]>('/ai/requests?limit=30'),
    ])
    setCapabilities(capabilityRows)
    setRequests(requestRows)
  }

  useEffect(() => { void load() }, [])

  const selectedCapability = useMemo(
    () => capabilities.find((row) => row.module_name === moduleName),
    [capabilities, moduleName],
  )

  useEffect(() => {
    if (selectedCapability && !selectedCapability.actions.includes(actionName)) {
      setActionName(selectedCapability.actions[0] ?? '')
    }
  }, [selectedCapability, actionName])

  async function generate(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setMessage('')
    try {
      const extra = JSON.parse(contextJson) as Record<string, unknown>
      const created = await api<AIRequest>('/ai/requests', {
        method: 'POST',
        body: JSON.stringify({
          module_name: moduleName,
          action_name: actionName,
          request_type: actionName === 'generate_image' ? 'image' : 'structured_text',
          input_data: { topic, title: topic, ...extra },
          parameters: {
            quantity: 5,
            panel_count: 8,
            purpose: moduleName === 'assessments' ? 'assessment_questions' : undefined,
          },
          queue_immediately: false,
        }),
      })
      const completed = await api<AIRequest>(`/ai/requests/${created.id}/run`, { method: 'POST' })
      setMessage(completed.status === 'completed'
        ? 'Proposta gerada e validada. Revise antes de aplicar.'
        : completed.error_message || 'A solicitação não foi concluída.')
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Falha na geração.')
    } finally {
      setBusy(false)
    }
  }

  async function review(resultId: string, decision: 'approved' | 'rejected') {
    setBusy(true)
    try {
      await api(`/ai/results/${resultId}/review`, {
        method: 'POST',
        body: JSON.stringify({
          decision,
          correctness_rating: decision === 'approved' ? 4 : 2,
          pedagogical_rating: decision === 'approved' ? 4 : 2,
          creativity_rating: 4,
          safety_rating: 5,
          comments: decision === 'approved' ? 'Revisado pelo professor.' : 'Resultado rejeitado para revisão.',
        }),
      })
      setMessage(decision === 'approved' ? 'Resultado aprovado.' : 'Resultado rejeitado.')
      await load()
    } finally { setBusy(false) }
  }

  return <div className="page-stack">
    <header className="page-header">
      <div><span className="eyebrow">Sprint 12</span><h1>EduCode AI Fabric</h1>
      <p>A camada inteligente conecta planejamento, RAG, HQs, avaliações, Analytics, intervenções, estatística e relatórios.</p></div>
    </header>

    {message ? <div className="notice success">{message}</div> : null}

    <section className="panel-grid two">
      <form className="panel" onSubmit={generate}>
        <h2>Nova assistência contextual</h2>
        <label>Módulo<select value={moduleName} onChange={(event) => setModuleName(event.target.value)}>
          {capabilities.filter((row) => row.enabled).map((row) => <option key={row.module_name} value={row.module_name}>{moduleLabels[row.module_name] ?? row.module_name}</option>)}
        </select></label>
        <label>Ação<select value={actionName} onChange={(event) => setActionName(event.target.value)}>
          {(selectedCapability?.actions ?? []).map((action) => <option key={action} value={action}>{action}</option>)}
        </select></label>
        <label>Tema ou objetivo<input value={topic} onChange={(event) => setTopic(event.target.value)} required /></label>
        <label>Contexto autorizado<textarea rows={8} value={contextJson} onChange={(event) => setContextJson(event.target.value)} /></label>
        <button disabled={busy || !actionName} type="submit">{busy ? 'Processando...' : 'Gerar proposta'}</button>
        <small>A IA propõe. O EduCode valida. O professor decide. A plataforma registra.</small>
      </form>

      <section className="panel">
        <h2>Integração ponta a ponta</h2>
        <div className="card-list">
          {capabilities.map((capability) => <article className="compact-card" key={capability.module_name}>
            <strong>{moduleLabels[capability.module_name] ?? capability.module_name}</strong>
            <span>{capability.actions.length} ações contextuais</span>
            <small>{capability.human_approval_required ? 'Revisão humana obrigatória' : 'Aplicação autorizada pela política'}</small>
          </article>)}
        </div>
      </section>
    </section>

    <section className="panel">
      <h2>Histórico auditável de gerações</h2>
      <div className="card-list">{requests.map((request) => {
        const result = request.results[0]
        return <article className="compact-card" key={request.id}>
          <strong>{moduleLabels[request.module_name] ?? request.module_name} · {request.action_name}</strong>
          <span>{request.flow_id} · {request.status} · custo estimado {request.estimated_cost.toFixed(6)}</span>
          {request.error_message ? <small>{request.error_message}</small> : null}
          {request.source_snapshot.citations?.length ? <small>Fontes: {request.source_snapshot.citations.map((citation) => citation.code).join(', ')}</small> : null}
          {result ? <>
            <pre className="json-preview">{JSON.stringify(result.structured_content, null, 2)}</pre>
            <span>Validação: {result.validation_results.valid ? 'aprovada' : 'pendente'} · Segurança: {result.safety_results.safe ? 'aprovada' : 'revisar'} · Revisão: {result.review_status}</span>
            <div className="button-row">
              <button disabled={busy || result.review_status === 'approved'} onClick={() => void review(result.id, 'approved')} type="button">Aprovar</button>
              <button className="secondary" disabled={busy} onClick={() => void review(result.id, 'rejected')} type="button">Rejeitar</button>
            </div>
          </> : null}
        </article>
      })}</div>
    </section>
  </div>
}
