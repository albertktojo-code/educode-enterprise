import { FormEvent, useEffect, useState } from 'react'

import { api } from '../lib/api'
import type { OrganizationDetails } from '../types/auth'

export function OrganizationPage() {
  const [organization, setOrganization] = useState<OrganizationDetails | null>(null)
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function load() {
    try {
      const data = await api<OrganizationDetails>('/organization')
      setOrganization(data)
      setName(data.name)
      setSlug(data.slug)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao carregar organização.')
    }
  }

  useEffect(() => {
    void load()
  }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSuccess('')
    try {
      const data = await api<OrganizationDetails>('/organization', {
        method: 'PATCH',
        body: JSON.stringify({ name, slug }),
      })
      setOrganization(data)
      setSuccess('Organização atualizada com sucesso.')
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao atualizar organização.')
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <span className="eyebrow">SPRINT 02 — MULTITENANCY</span>
          <h1>Organização</h1>
          <p>Configurações do ambiente isolado por organização.</p>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}

      <div className="two-columns">
        <form className="panel form-grid" onSubmit={submit}>
          <h2>Dados gerais</h2>
          <label>
            Nome
            <input value={name} onChange={(event) => setName(event.target.value)} required />
          </label>
          <label>
            Identificador
            <input value={slug} onChange={(event) => setSlug(event.target.value)} required />
          </label>
          <button className="primary">Salvar organização</button>
        </form>

        <div className="panel detail-list">
          <h2>Informações</h2>
          <div><span>ID</span><strong className="mono">{organization?.id ?? '-'}</strong></div>
          <div><span>Status</span><strong>{organization?.is_active ? 'Ativa' : 'Inativa'}</strong></div>
          <div><span>Criada em</span><strong>{organization ? new Date(organization.created_at).toLocaleString('pt-BR') : '-'}</strong></div>
          <div><span>Atualizada em</span><strong>{organization ? new Date(organization.updated_at).toLocaleString('pt-BR') : '-'}</strong></div>
        </div>
      </div>
    </section>
  )
}
