import { FormEvent, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { api } from '../lib/api'

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = useMemo(() => searchParams.get('token') ?? '', [searchParams])
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setMessage('')
    if (!token) {
      setError('O link de recuperação não contém um token válido.')
      return
    }
    if (password !== confirmation) {
      setError('A confirmação da senha não confere.')
      return
    }
    setSending(true)
    try {
      await api<void>('/auth/reset-password', {
        method: 'POST',
        auth: false,
        body: JSON.stringify({
          token,
          new_password: password,
          confirm_password: confirmation,
        }),
      })
      setMessage('Senha redefinida. Todas as sessões anteriores foram encerradas.')
      setPassword('')
      setConfirmation('')
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível redefinir a senha.',
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
            <small>Nova senha</small>
          </div>
        </div>

        <h1>Redefinir senha</h1>
        <p>
          Use ao menos 10 caracteres, com maiúscula, minúscula, número e
          caractere especial.
        </p>

        <label htmlFor="new-password">
          Nova senha
          <div className="password-field">
            <input
              id="new-password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={10}
              required
            />
            <button
              className="password-toggle"
              type="button"
              onClick={() => setShowPassword((value) => !value)}
            >
              {showPassword ? 'Ocultar' : 'Mostrar'}
            </button>
          </div>
        </label>

        <label htmlFor="confirm-password">
          Confirmar nova senha
          <input
            id="confirm-password"
            type={showPassword ? 'text' : 'password'}
            autoComplete="new-password"
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
            minLength={10}
            required
          />
        </label>

        {message ? <div className="alert success">{message}</div> : null}
        {error ? <div className="alert error">{error}</div> : null}

        <button className="primary" type="submit" disabled={sending}>
          {sending ? 'Redefinindo...' : 'Redefinir senha'}
        </button>

        <Link to="/login">Ir para o login</Link>
      </form>
    </main>
  )
}
