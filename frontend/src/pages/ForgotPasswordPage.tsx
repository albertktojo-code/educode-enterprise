import { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSending(true)
    setError('')
    setMessage('')
    try {
      const result = await api<{ message: string }>('/auth/forgot-password', {
        method: 'POST',
        auth: false,
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      })
      setMessage(result.message)
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível processar a solicitação.',
      )
    } finally {
      setSending(false)
    }
  }

  return (
    <main className="auth-public-page">
      <form className="login-card auth-public-card" onSubmit={submit}>
        <div className="brand login-brand">
          <span className="brand-mark">EC</span>
          <div>
            <strong>EduCode</strong>
            <small>Recuperação de acesso</small>
          </div>
        </div>

        <h1>Esqueci minha senha</h1>
        <p>
          Informe seu e-mail. A resposta será a mesma para endereços
          cadastrados ou não cadastrados.
        </p>

        <label htmlFor="recovery-email">
          E-mail
          <input
            id="recovery-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>

        {message ? <div className="alert success">{message}</div> : null}
        {error ? <div className="alert error">{error}</div> : null}

        <button className="primary" type="submit" disabled={sending}>
          {sending ? 'Enviando...' : 'Enviar instruções'}
        </button>

        <Link to="/login">Voltar ao login</Link>
      </form>
    </main>
  )
}
