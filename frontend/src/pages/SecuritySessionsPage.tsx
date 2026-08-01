import { useEffect, useState } from 'react'

import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import type { AuthSession } from '../types/auth'

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function SecuritySessionsPage() {
  const { logout } = useAuth()
  const [sessions, setSessions] = useState<AuthSession[]>([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busyId, setBusyId] = useState<string | null>(null)

  async function load(): Promise<void> {
    try {
      setSessions(await api.get<AuthSession[]>('/auth/sessions'))
      setError('')
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível carregar as sessões.',
      )
    }
  }

  useEffect(() => {
    void load()
  }, [])

  async function revoke(item: AuthSession): Promise<void> {
    setBusyId(item.id)
    setError('')
    setMessage('')
    try {
      await api.delete<void>(`/auth/sessions/${item.id}`)
      if (item.current) {
        await logout()
        return
      }
      setMessage('Sessão encerrada.')
      await load()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível encerrar a sessão.',
      )
    } finally {
      setBusyId(null)
    }
  }

  async function revokeOthers(): Promise<void> {
    setBusyId('others')
    setError('')
    setMessage('')
    try {
      const result = await api.post<{ revoked: number }>(
        '/auth/sessions/revoke-all',
        { keep_current: true },
      )
      setMessage(`${result.revoked} sessão(ões) encerrada(s).`)
      await load()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível encerrar as outras sessões.',
      )
    } finally {
      setBusyId(null)
    }
  }

  async function revokeAll(): Promise<void> {
    setBusyId('all')
    setError('')
    try {
      await api.post<{ revoked: number }>('/auth/sessions/revoke-all', {
        keep_current: false,
      })
      await logout()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível encerrar todas as sessões.',
      )
    } finally {
      setBusyId(null)
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <span className="eyebrow">SEGURANÇA DA CONTA</span>
          <h1>Sessões ativas</h1>
          <p>
            Revise os navegadores conectados e encerre acessos que você não
            reconhece.
          </p>
        </div>
        <div className="button-row">
          <button
            type="button"
            disabled={busyId !== null}
            onClick={() => void revokeOthers()}
          >
            Encerrar outras sessões
          </button>
          <button
            className="danger-button"
            type="button"
            disabled={busyId !== null}
            onClick={() => void revokeAll()}
          >
            Sair de todos os dispositivos
          </button>
        </div>
      </header>

      {message ? <div className="alert success">{message}</div> : null}
      {error ? <div className="alert error">{error}</div> : null}

      <div className="security-session-list">
        {sessions.map((item) => (
          <article className="panel security-session-card" key={item.id}>
            <div>
              <h2>
                {item.device_name}
                {item.current ? <span className="current-session-chip">Atual</span> : null}
              </h2>
              <p>
                Último IP: {item.last_ip_masked || 'não informado'}
                {' · '}Último uso: {formatDate(item.last_used_at)}
              </p>
              <small>
                Criada em {formatDate(item.created_at)}
                {' · '}Expira em {formatDate(item.expires_at)}
                {item.remember_me ? ' · Mantenha-me conectado' : ''}
              </small>
            </div>
            <button
              type="button"
              disabled={busyId !== null}
              onClick={() => void revoke(item)}
            >
              {busyId === item.id ? 'Encerrando...' : 'Encerrar sessão'}
            </button>
          </article>
        ))}
      </div>

      {!sessions.length && !error ? (
        <div className="panel">Nenhuma sessão ativa foi encontrada.</div>
      ) : null}
    </section>
  )
}
