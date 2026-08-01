import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'

type Notification = {
  id: string
  job_id: string
  notification_type: string
  title: string
  message: string
  action_path: string | null
  status: string
  created_at: string
}

export function NotificationsPage() {
  const [items, setItems] = useState<Notification[]>([])

  async function load() {
    setItems(await api<Notification[]>('/notifications'))
  }

  useEffect(() => { void load() }, [])

  async function markRead(id: string) {
    await api(`/notifications/${id}/read`, { method: 'PATCH' })
    await load()
  }

  return <div className="page-stack">
    <header className="page-header"><div><span className="eyebrow">Central de notificações</span><h1>Notificações</h1><p>Conclusões, falhas e solicitações de atenção relacionadas às tarefas do EduCode.</p></div></header>
    <section className="panel"><div className="card-list">{items.length ? items.map((item) => <article className={`compact-card ${item.status === 'unread' ? 'unread-card' : ''}`} key={item.id}><strong>{item.title}</strong><span>{item.message}</span><small>{new Date(item.created_at).toLocaleString('pt-BR')}</small><div className="button-row"><Link className="secondary-button" to={item.action_path ?? `/tarefas/${item.job_id}`}>Abrir tarefa</Link>{item.status === 'unread' ? <button type="button" onClick={() => void markRead(item.id)}>Marcar como lida</button> : null}</div></article>) : <p>Nenhuma notificação.</p>}</div></section>
  </div>
}
