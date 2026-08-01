import { FormEvent, useEffect, useMemo, useState } from 'react'

import { api } from '../lib/api'

type Provider = { id: string; name: string; provider_type: string; status: string; base_url: string | null; secret_env_var: string | null }
type Model = { id: string; provider_id: string; name: string; model_identifier: string; capabilities: string[]; is_default: boolean }
type Policy = { module_name: string; enabled: boolean; daily_request_limit: number; monthly_cost_limit: number; human_approval_required: boolean }
type Usage = { request_count: number; completed_count: number; failed_count: number; image_count: number; estimated_cost: number; by_module: Record<string, Record<string, number>> }

export function AdminAIPage() {
  const [providers, setProviders] = useState<Provider[]>([])
  const [models, setModels] = useState<Model[]>([])
  const [policies, setPolicies] = useState<Policy[]>([])
  const [usage, setUsage] = useState<Usage | null>(null)
  const [name, setName] = useState('Mock institucional')
  const [providerType, setProviderType] = useState('mock')
  const [baseUrl, setBaseUrl] = useState('')
  const [secretEnvVar, setSecretEnvVar] = useState('EDUCODE_AI_API_KEY')
  const [message, setMessage] = useState('')

  async function load() {
    const [providerRows, modelRows, policyRows, summary] = await Promise.all([
      api<Provider[]>('/ai/admin/providers'),
      api<Model[]>('/ai/admin/models'),
      api<Policy[]>('/ai/admin/policies'),
      api<Usage>('/ai/admin/usage'),
    ])
    setProviders(providerRows); setModels(modelRows); setPolicies(policyRows); setUsage(summary)
  }
  useEffect(() => { void load() }, [])

  async function createProvider(event: FormEvent) {
    event.preventDefault()
    await api('/ai/admin/providers', {
      method: 'POST',
      body: JSON.stringify({
        name,
        provider_type: providerType,
        base_url: providerType === 'generic_http' ? baseUrl : null,
        secret_env_var: providerType === 'generic_http' ? secretEnvVar : null,
        public_configuration: providerType === 'generic_http' ? { endpoint: '/generate', text_path: 'text', structured_path: 'structured' } : {},
        timeout_seconds: 60,
      }),
    })
    setMessage('Provedor cadastrado sem armazenar o segredo no banco.')
    await load()
  }

  async function createModel(provider: Provider) {
    await api('/ai/admin/models', {
      method: 'POST',
      body: JSON.stringify({
        provider_id: provider.id,
        name: `${provider.name} — padrão`,
        model_identifier: provider.provider_type === 'mock' ? 'educode-mock-v2' : 'configured-model',
        capabilities: ['structured_text', 'text', 'image'],
        configuration: {},
        is_default: models.length === 0,
        input_unit_cost: 0,
        output_unit_cost: 0,
        image_unit_cost: 0,
      }),
    })
    await load()
  }

  async function createDefaultPolicies() {
    const modules = ['planning', 'rag', 'comics', 'assets', 'assessments', 'grading', 'analytics', 'interventions', 'statistics', 'reports', 'accessibility']
    for (const moduleName of modules) {
      await api(`/ai/admin/policies/${moduleName}`, {
        method: 'PUT',
        body: JSON.stringify({
          module_name: moduleName,
          enabled: true,
          allowed_actions: [],
          allowed_model_ids: [],
          human_approval_required: true,
          daily_request_limit: 100,
          monthly_cost_limit: 100,
          allow_student_data: false,
          allow_real_person_images: false,
          fallback_mode: 'mock',
          policy_configuration: { anonymize_student_context: true },
        }),
      })
    }
    setMessage('Políticas seguras criadas para todos os módulos.')
    await load()
  }

  const totals = useMemo(() => ({ providers: providers.length, models: models.length, policies: policies.length }), [providers, models, policies])

  return <div className="page-stack">
    <header className="page-header"><div><span className="eyebrow">Administração</span><h1>Inteligência Artificial</h1>
      <p>Gerencie provedores, modelos, permissões, limites e consumo da camada transversal de IA.</p></div></header>
    {message ? <div className="notice success">{message}</div> : null}

    <section className="dashboard-grid four">
      <article className="metric-card"><span>Provedores</span><strong>{totals.providers}</strong></article>
      <article className="metric-card"><span>Modelos</span><strong>{totals.models}</strong></article>
      <article className="metric-card"><span>Políticas</span><strong>{totals.policies}</strong></article>
      <article className="metric-card"><span>Custo estimado</span><strong>{usage?.estimated_cost.toFixed(4) ?? '0'}</strong></article>
    </section>

    <section className="panel-grid two">
      <form className="panel" onSubmit={createProvider}>
        <h2>Novo provedor</h2>
        <label>Nome<input value={name} onChange={(event) => setName(event.target.value)} required /></label>
        <label>Tipo<select value={providerType} onChange={(event) => setProviderType(event.target.value)}><option value="mock">Mock local</option><option value="generic_http">HTTP genérico</option></select></label>
        {providerType === 'generic_http' ? <>
          <label>URL base<input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} placeholder="https://gateway.institucional.example" required /></label>
          <label>Variável do segredo<input value={secretEnvVar} onChange={(event) => setSecretEnvVar(event.target.value)} required /></label>
        </> : null}
        <button type="submit">Cadastrar provedor</button>
        <small>A credencial permanece no ambiente do backend e nunca é enviada ao navegador.</small>
      </form>

      <section className="panel"><h2>Governança institucional</h2>
        <p>As políticas bloqueiam publicação automática, exposição de dados estudantis e custos acima dos limites definidos.</p>
        <button onClick={() => void createDefaultPolicies()} type="button">Criar políticas seguras padrão</button>
        <div className="card-list">{policies.map((policy) => <article className="compact-card" key={policy.module_name}><strong>{policy.module_name}</strong><span>{policy.enabled ? 'Ativo' : 'Desativado'} · {policy.daily_request_limit}/dia</span><small>Revisão humana: {policy.human_approval_required ? 'obrigatória' : 'conforme fluxo'}</small></article>)}</div>
      </section>
    </section>

    <section className="panel"><h2>Provedores e modelos</h2><div className="card-list">
      {providers.map((provider) => <article className="compact-card" key={provider.id}><strong>{provider.name}</strong><span>{provider.provider_type} · {provider.status}</span><small>{provider.base_url ?? 'Execução local mock'}</small><button onClick={() => void createModel(provider)} type="button">Adicionar modelo</button></article>)}
      {models.map((model) => <article className="compact-card" key={model.id}><strong>{model.name}</strong><span>{model.model_identifier} · {model.capabilities.join(', ')}</span><small>{model.is_default ? 'Modelo padrão' : 'Modelo opcional'}</small></article>)}
    </div></section>

    <section className="panel"><h2>Consumo e observabilidade</h2>
      <p>{usage?.request_count ?? 0} solicitações · {usage?.completed_count ?? 0} concluídas · {usage?.failed_count ?? 0} falhas · {usage?.image_count ?? 0} imagens.</p>
      <div className="card-list">{Object.entries(usage?.by_module ?? {}).map(([moduleName, values]) => <article className="compact-card" key={moduleName}><strong>{moduleName}</strong><span>{values.requests ?? 0} solicitações</span><small>Custo estimado: {Number(values.cost ?? 0).toFixed(6)}</small></article>)}</div>
    </section>
  </div>
}
