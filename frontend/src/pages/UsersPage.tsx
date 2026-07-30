import { FormEvent, useEffect, useMemo, useState } from 'react'

import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import type { Role, UserListItem } from '../types/auth'

const roleLabels: Record<Role, string> = {
  owner: 'Proprietário',
  admin: 'Administrador',
  teacher: 'Professor',
  member: 'Membro',
}

const emptyForm = {
  full_name: '',
  email: '',
  password: '',
  role: 'member' as Role,
}

export function UsersPage() {
  const { user } = useAuth()
  const [users, setUsers] = useState<UserListItem[]>([])
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [filter, setFilter] = useState<'all' | 'active' | 'inactive'>('all')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function load() {
    try {
      setUsers(await api<UserListItem[]>('/users'))
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao carregar usuários.')
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const visibleUsers = useMemo(() => {
    if (filter === 'all') return users
    return users.filter((item) => item.is_active === (filter === 'active'))
  }, [filter, users])

  function beginEdit(item: UserListItem) {
    setEditingId(item.id)
    setForm({
      full_name: item.full_name,
      email: item.email,
      password: '',
      role: item.role,
    })
    setError('')
    setSuccess('')
  }

  function cancelEdit() {
    setEditingId(null)
    setForm(emptyForm)
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSuccess('')
    try {
      if (editingId) {
        await api<UserListItem>(`/users/${editingId}`, {
          method: 'PATCH',
          body: JSON.stringify({
            full_name: form.full_name,
            role: form.role,
          }),
        })
        setSuccess('Usuário atualizado com sucesso.')
      } else {
        await api<UserListItem>('/users', {
          method: 'POST',
          body: JSON.stringify(form),
        })
        setSuccess('Usuário cadastrado com sucesso.')
      }
      cancelEdit()
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao salvar usuário.')
    }
  }

  async function toggleActive(item: UserListItem) {
    setError('')
    try {
      await api<UserListItem>(`/users/${item.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !item.is_active }),
      })
      setSuccess(item.is_active ? 'Usuário desativado.' : 'Usuário reativado.')
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao alterar status.')
    }
  }

  async function resetPassword(item: UserListItem) {
    const newPassword = window.prompt(
      `Digite a nova senha de ${item.full_name} (mínimo de 8 caracteres):`,
    )
    if (!newPassword) return
    if (newPassword.length < 8) {
      setError('A nova senha deve ter pelo menos 8 caracteres.')
      return
    }
    try {
      await api<void>(`/users/${item.id}/reset-password`, {
        method: 'POST',
        body: JSON.stringify({ new_password: newPassword }),
      })
      setSuccess('Senha redefinida com sucesso.')
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao redefinir senha.')
    }
  }

  async function removeUser(item: UserListItem) {
    const confirmed = window.confirm(
      `Remover ${item.full_name} desta organização?`,
    )
    if (!confirmed) return
    try {
      await api<void>(`/users/${item.id}`, { method: 'DELETE' })
      setSuccess('Acesso removido da organização.')
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao remover usuário.')
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <span className="eyebrow">SPRINT 02 — USUÁRIOS E RBAC</span>
          <h1>Usuários</h1>
          <p>Cadastre, edite, ative, desative e gerencie papéis e senhas.</p>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {success ? <div className="alert success">{success}</div> : null}

      <div className="filter-bar">
        {(['all', 'active', 'inactive'] as const).map((item) => (
          <button
            type="button"
            key={item}
            className={filter === item ? 'filter active' : 'filter'}
            onClick={() => setFilter(item)}
          >
            {item === 'all' ? 'Todos' : item === 'active' ? 'Ativos' : 'Inativos'}
          </button>
        ))}
      </div>

      <section className="two-columns">
        <form className="panel form-grid" onSubmit={submit}>
          <div className="panel-title-row">
            <h2>{editingId ? 'Editar usuário' : 'Novo usuário'}</h2>
            {editingId ? (
              <button type="button" className="text-button" onClick={cancelEdit}>
                Cancelar
              </button>
            ) : null}
          </div>

          <label>
            Nome completo
            <input
              value={form.full_name}
              onChange={(event) => setForm({ ...form, full_name: event.target.value })}
              required
              minLength={3}
            />
          </label>

          <label>
            E-mail
            <input
              type="email"
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
              required
              disabled={Boolean(editingId)}
            />
          </label>

          {!editingId ? (
            <label>
              Senha inicial
              <input
                type="password"
                value={form.password}
                onChange={(event) => setForm({ ...form, password: event.target.value })}
                required
                minLength={8}
              />
            </label>
          ) : null}

          <label>
            Papel
            <select
              value={form.role}
              onChange={(event) => setForm({ ...form, role: event.target.value as Role })}
            >
              <option value="member">Membro</option>
              <option value="teacher">Professor</option>
              <option value="admin">Administrador</option>
              <option value="owner">Proprietário</option>
            </select>
          </label>

          <button className="primary">
            {editingId ? 'Salvar alterações' : 'Cadastrar usuário'}
          </button>
        </form>

        <section className="panel">
          <div className="panel-title-row">
            <h2>Equipe</h2>
            <span>{visibleUsers.length} usuário(s)</span>
          </div>

          <div className="user-list detailed-list">
            {visibleUsers.map((item) => (
              <article key={item.id} className={!item.is_active ? 'inactive-card' : ''}>
                <div className="avatar">{item.full_name.slice(0, 2).toUpperCase()}</div>
                <div>
                  <strong>{item.full_name}</strong>
                  <span>{item.email}</span>
                  <small>{item.is_active ? 'Ativo' : 'Inativo'}</small>
                </div>
                <div className="vertical-actions">
                  <span className="role-chip">{roleLabels[item.role]}</span>
                  <div className="card-actions compact">
                    <button type="button" onClick={() => beginEdit(item)}>Editar</button>
                    <button
                      type="button"
                      onClick={() => void toggleActive(item)}
                      disabled={item.id === user?.id}
                    >
                      {item.is_active ? 'Desativar' : 'Ativar'}
                    </button>
                    <button type="button" onClick={() => void resetPassword(item)}>
                      Nova senha
                    </button>
                    <button
                      type="button"
                      className="danger-button"
                      onClick={() => void removeUser(item)}
                      disabled={item.id === user?.id}
                    >
                      Remover
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>
      </section>
    </section>
  )
}
