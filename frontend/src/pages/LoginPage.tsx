import { FormEvent, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../contexts/AuthContext'

export function LoginPage() {
  const { user, login } = useAuth()
  const [email, setEmail] = useState(
    import.meta.env.VITE_INITIAL_ADMIN_EMAIL ?? '',
  )
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  if (user) return <Navigate to="/" replace />

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSending(true)
    try {
      await login(email, password, rememberMe)
      const destination =
        (location.state as { from?: string } | null)?.from ?? '/'
      navigate(destination, { replace: true })
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Não foi possível realizar o login.',
      )
    } finally {
      setSending(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-hero">
        <div className="hero-copy">
          <span className="eyebrow">PLATAFORMA EDUCACIONAL INTELIGENTE</span>
          <h1>Crie, organize e escale experiências de aprendizagem.</h1>
          <p>
            Projetos, turmas, HQs educativas, avaliações, analytics e IA em
            uma arquitetura preparada para BNCC e Pensamento Computacional.
          </p>
        </div>
      </section>

      <section className="login-panel">
        <form className="login-card" onSubmit={submit}>
          <div className="brand login-brand">
            <span className="brand-mark">EC</span>
            <div>
              <strong>EduCode</strong>
              <small>Enterprise 2.0</small>
            </div>
          </div>

          <h2>Acesse sua conta</h2>
          <p>Use suas credenciais institucionais.</p>

          <label htmlFor="email">
            E-mail
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>

          <label htmlFor="password">
            Senha
            <div className="password-field">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                minLength={8}
                required
              />
              <button
                type="button"
                className="password-toggle"
                aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                onClick={() => setShowPassword((value) => !value)}
              >
                {showPassword ? 'Ocultar' : 'Mostrar'}
              </button>
            </div>
          </label>

          <div className="login-options">
            <label className="checkbox-row" htmlFor="remember-me">
              <input
                id="remember-me"
                type="checkbox"
                checked={rememberMe}
                onChange={(event) => setRememberMe(event.target.checked)}
              />
              Mantenha-me conectado
            </label>
            <Link to="/forgot-password">Esqueci minha senha</Link>
          </div>

          {error ? <div className="alert error">{error}</div> : null}

          <button className="primary" type="submit" disabled={sending}>
            {sending ? 'Entrando...' : 'Entrar com segurança'}
          </button>

          <small className="hint">
            A opção de permanência usa uma sessão revogável e não armazena sua
            senha no navegador.
          </small>
          <Link className="login-certificate-link" to="/credentials/verificar">
            Verificar um certificado EduCode
          </Link>
        </form>
      </section>
    </main>
  )
}
