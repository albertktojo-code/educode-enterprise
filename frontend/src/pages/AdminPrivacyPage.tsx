import { useEffect, useState } from 'react'

import { api } from '../lib/api'

type Policy = {
  id: string
  data_type: string
  retention_days: number
  anonymize_after_days: number | null
  delete_after_days: number | null
  legal_basis: string
  is_active: boolean
}

const defaults = [
  ['technical_logs', 90, 'Segurança e operação'],
  ['critical_audit', 1825, 'Obrigação legal e proteção institucional'],
  ['anonymized_ai_prompts', 180, 'Melhoria controlada do serviço'],
  ['temporary_files', 7, 'Execução técnica temporária'],
  ['student_learning_records', 1825, 'Execução da política educacional'],
]

export function AdminPrivacyPage() {
  const [policies, setPolicies] = useState<Policy[]>([])
  const [message, setMessage] = useState('')

  async function load() {
    setPolicies(await api.get<Policy[]>('/platform/retention-policies'))
  }

  useEffect(() => { void load() }, [])

  async function seedDefaults() {
    for (const [dataType, days, legalBasis] of defaults) {
      await api.put(`/platform/retention-policies/${dataType}`, {
        data_type: dataType,
        retention_days: days,
        anonymize_after_days: null,
        delete_after_days: days,
        legal_basis: legalBasis,
        is_active: true,
      })
    }
    setMessage('Políticas recomendadas cadastradas.')
    await load()
  }

  async function updatePolicy(policy: Policy, changes: Partial<Policy>) {
    const next = { ...policy, ...changes }
    await api.put(`/platform/retention-policies/${policy.data_type}`, {
      data_type: next.data_type,
      retention_days: next.retention_days,
      anonymize_after_days: next.anonymize_after_days,
      delete_after_days: next.delete_after_days,
      legal_basis: next.legal_basis,
      is_active: next.is_active,
    })
    await load()
  }

  return <div className="page-stack">
    <header className="page-header"><div><span className="eyebrow">LGPD</span><h1>Privacidade e retenção</h1><p>Defina por quanto tempo cada categoria de dado permanece disponível, anonimizada ou eliminada.</p></div><button type="button" onClick={() => void seedDefaults()}>Aplicar políticas recomendadas</button></header>
    {message ? <div className="notice">{message}</div> : null}
    <section className="panel"><h2>Políticas da organização</h2><div className="card-list">{policies.length ? policies.map((policy) => <article className="compact-card" key={policy.id}><strong>{policy.data_type}</strong><span>Retenção: {policy.retention_days} dias · Exclusão: {policy.delete_after_days ?? 'não definida'} dias</span><small>{policy.legal_basis}</small><div className="inline-form"><input type="number" min="1" value={policy.retention_days} onChange={(event) => setPolicies((rows) => rows.map((row) => row.id === policy.id ? { ...row, retention_days: Number(event.target.value) } : row))}/><button className="secondary-button" type="button" onClick={() => void updatePolicy(policy, {})}>Salvar</button><button className="secondary-button" type="button" onClick={() => void updatePolicy(policy, { is_active: !policy.is_active })}>{policy.is_active ? 'Desativar' : 'Ativar'}</button></div></article>) : <p>Nenhuma política cadastrada.</p>}</div></section>
  </div>
}
