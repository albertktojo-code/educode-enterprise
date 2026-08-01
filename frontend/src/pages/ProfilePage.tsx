import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import type { User } from '../types/auth'

export function ProfilePage() {
  const { user, refreshUser, logout } = useAuth()
  const [fullName, setFullName] = useState(user?.full_name ?? '')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => setFullName(user?.full_name ?? ''), [user])

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSuccess('')
    try {
      await api<User>('/auth/me', {
        method: 'PATCH',
        body: JSON.stringify({ full_name: fullName }),
      })
      await refreshUser()
      setSuccess('Perfil atualizado com sucesso.')
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao atualizar perfil.')
    }
  }

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSuccess('')
    if (newPassword !== confirmPassword) {
      setError('A confirmação da nova senha não confere.')
      return
    }
    try {
      await api<void>('/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setSuccess('Senha alterada. Entre novamente com a nova senha.')
      window.setTimeout(() => void logout(), 1200)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao alterar senha.')
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <span className="eyebrow">CONTA</span>
          <h1>Meu perfil</h1>
          <p>Atualize seu nome, sua senha e revise as sessões conectadas.</p>
          <Link to="/account/security">Gerenciar sessões ativas</Link>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}

      <div className="two-columns">
        <form className="panel form-grid" onSubmit={saveProfile}>
          <h2>Dados pessoais</h2>
          <label>
            Nome completo
            <input value={fullName} onChange={(event) => setFullName(event.target.value)} required minLength={3} />
          </label>
          <label>
            E-mail
            <input value={user?.email ?? ''} disabled />
          </label>
          <button className="primary">Salvar perfil</button>
        </form>

        <form className="panel form-grid" onSubmit={changePassword}>
          <h2>Alterar senha</h2>
          <label>
            Senha atual
            <input type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required minLength={8} />
          </label>
          <label>
            Nova senha
            <input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required minLength={8} />
          </label>
          <label>
            Confirmar nova senha
            <input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required minLength={8} />
          </label>
          <button className="primary">Alterar senha</button>
        </form>
      </div>

      <section className="panel profile-grid">
        <div><span>Status</span><strong>{user?.is_active ? 'Ativo' : 'Inativo'}</strong></div>
        <div><span>Superusuário</span><strong>{user?.is_superuser ? 'Sim' : 'Não'}</strong></div>
        <div><span>Organização</span><strong>{user?.memberships[0]?.organization.name}</strong></div>
        <div><span>Papel</span><strong>{user?.memberships[0]?.role}</strong></div>
      </section>
    </section>
  )
}
