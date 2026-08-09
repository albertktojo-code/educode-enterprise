import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { EmptyState } from '../components/EmptyState'
import { LoadingState } from '../components/LoadingState'
import { studentNotificationsApi } from '../features/connect/notificationsApi'
import type { NotificationItem } from '../types/delivery'
import './studentNotifications.css'

type NotificationFilter = 'all' | 'unread' | 'learning' | 'credentials' | 'communication'

function category(item: NotificationItem): 'credentials' | 'learning' | 'communication' {
  if (item.notification_type.startsWith('certificate_')) return 'credentials'
  if (item.notification_type === 'classroom_announcement') return 'communication'
  return 'learning'
}

export function StudentNotificationsPage() {
  const [items, setItems] = useState<NotificationItem[]>([])
  const [filter, setFilter] = useState<NotificationFilter>('all')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')

  useEffect(() => {
    let active = true
    void studentNotificationsApi.list()
      .then((notifications) => { if (active) setItems(notifications) })
      .catch((error: unknown) => { if (active) setNotice(error instanceof Error ? error.message : 'Não foi possível carregar as notificações.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  const unread = items.filter((item) => item.status === 'unread').length
  const visible = useMemo(() => items.filter((item) => {
    if (filter === 'all') return true
    if (filter === 'unread') return item.status === 'unread'
    return category(item) === filter
  }), [filter, items])

  async function markRead(id: string) {
    setBusy(true)
    setNotice('')
    try {
      const updated = await studentNotificationsApi.markRead(id)
      setItems((current) => current.map((item) => item.id === updated.id ? updated : item))
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Não foi possível atualizar a notificação.')
    } finally {
      setBusy(false)
    }
  }

  async function markAllRead() {
    setBusy(true)
    setNotice('')
    try {
      const result = await studentNotificationsApi.markAllRead()
      const readAt = new Date().toISOString()
      setItems((current) => current.map((item) => item.status === 'unread' ? { ...item, status: 'read', read_at: readAt } : item))
      setNotice(`${result.updated} notificação(ões) marcada(s) como lida(s).`)
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Não foi possível atualizar as notificações.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="student-notifications" aria-busy={loading}>
      <header className="student-notifications-hero"><div><span>EDUCODE CONNECT</span><h1>Minhas notificações</h1><p>Acompanhe atividades, resultados e conquistas importantes da sua jornada.</p></div><div><strong>{unread}</strong><span>não lida(s)</span></div></header>
      <div className="student-notifications-toolbar">
        <div role="group" aria-label="Filtrar notificações">{(['all', 'unread', 'learning', 'credentials', 'communication'] as const).map((value) => <button type="button" key={value} className={filter === value ? 'active' : ''} aria-pressed={filter === value} onClick={() => setFilter(value)}>{value === 'all' ? 'Todas' : value === 'unread' ? 'Não lidas' : value === 'learning' ? 'Aprendizagem' : value === 'credentials' ? 'Certificados' : 'Comunicados'}</button>)}</div>
        <button type="button" onClick={() => void markAllRead()} disabled={busy || unread === 0}>Marcar todas como lidas</button>
      </div>
      <p className="student-notifications-notice" aria-live="polite">{notice}</p>
      {loading ? <LoadingState label="Carregando notificações" rows={4} /> : null}
      {!loading && visible.length ? <div className="student-notifications-list">{visible.map((item) => <article key={item.id} className={item.status === 'unread' ? 'is-unread' : ''}>
        <span className="student-notifications-icon" aria-hidden="true">{category(item) === 'credentials' ? '◆' : category(item) === 'communication' ? '◉' : '●'}</span>
        <div><small>{category(item) === 'credentials' ? 'CERTIFICADO' : category(item) === 'communication' ? 'COMUNICADO' : 'APRENDIZAGEM'} · {new Date(item.created_at).toLocaleString('pt-BR')}</small><h2>{item.title}</h2><p>{item.message}</p><div>{item.action_path ? <Link to={item.action_path}>Abrir</Link> : null}{item.status === 'unread' ? <button type="button" disabled={busy} onClick={() => void markRead(item.id)}>Marcar como lida</button> : <span>Lida</span>}</div></div>
      </article>)}</div> : null}
      {!loading && !visible.length ? <EmptyState icon="activity" title="Nenhuma notificação neste filtro" description="Novas atividades, resultados e certificados aparecerão aqui." /> : null}
    </section>
  )
}
