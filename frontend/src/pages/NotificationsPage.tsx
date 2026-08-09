import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { teacherAnnouncementsApi } from '../features/connect/notificationsApi'
import { api } from '../lib/api'
import type { Classroom } from '../types/education'
import './teacherAnnouncements.css'

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
  const [classrooms, setClassrooms] = useState<Classroom[]>([])
  const [selectedClassrooms, setSelectedClassrooms] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')

  async function load() {
    const [notifications, classroomItems] = await Promise.all([
      api.get<Notification[]>('/notifications'),
      api.get<Classroom[]>('/classrooms'),
    ])
    setItems(notifications)
    setClassrooms(classroomItems.filter((item) => item.is_active))
  }

  useEffect(() => {
    void load()
      .catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'Não foi possível carregar a central.'))
      .finally(() => setLoading(false))
  }, [])

  async function markRead(id: string) {
    await api.patch(`/notifications/${id}/read`)
    await load()
  }

  function toggleClassroom(id: string) {
    setSelectedClassrooms((current) => current.includes(id)
      ? current.filter((item) => item !== id)
      : [...current, id])
  }

  async function sendAnnouncement(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedClassrooms.length) {
      setNotice('Selecione ao menos uma turma.')
      return
    }
    const form = event.currentTarget
    const values = new FormData(form)
    setBusy(true)
    setNotice('')
    try {
      const result = await teacherAnnouncementsApi.send({
        classroom_ids: selectedClassrooms,
        title: String(values.get('title') ?? ''),
        message: String(values.get('message') ?? ''),
        action_path: String(values.get('action_path') ?? '/aluno'),
      })
      form.reset()
      setSelectedClassrooms([])
      setNotice(`Comunicado entregue a ${result.recipients} estudante(s) de ${result.classrooms} turma(s).`)
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Não foi possível enviar o comunicado.')
    } finally {
      setBusy(false)
    }
  }

  return <section className="teacher-announcements" aria-busy={loading}>
    <header className="teacher-announcements-hero"><div><span>EDUCODE CONNECT</span><h1>Comunicação e notificações</h1><p>Envie orientações às turmas e acompanhe processamentos que precisam da sua atenção.</p></div></header>
    <p className="teacher-announcements-notice" aria-live="polite">{notice}</p>
    <div className="teacher-announcements-grid">
      <form className="panel teacher-announcements-form" onSubmit={(event) => void sendAnnouncement(event)}>
        <header><span>COMUNICADO ÀS TURMAS</span><h2>Nova mensagem</h2></header>
        <fieldset><legend>Turmas destinatárias</legend>{classrooms.length ? <div>{classrooms.map((classroom) => <label key={classroom.id}><input type="checkbox" checked={selectedClassrooms.includes(classroom.id)} onChange={() => toggleClassroom(classroom.id)} />{classroom.name}</label>)}</div> : <p>Nenhuma turma ativa disponível.</p>}</fieldset>
        <label htmlFor="announcement-title">Título<input id="announcement-title" name="title" minLength={3} maxLength={240} required placeholder="Ex.: Orientações para esta semana" /></label>
        <label htmlFor="announcement-message">Mensagem<textarea id="announcement-message" name="message" minLength={3} maxLength={2000} rows={5} required /></label>
        <label htmlFor="announcement-action">Destino ao abrir<select id="announcement-action" name="action_path" defaultValue="/aluno"><option value="/aluno">Início do estudante</option><option value="/aluno/atividades">Atividades</option><option value="/aluno/portfolio">Portfólio</option><option value="/aluno/notificacoes">Notificações</option></select></label>
        <button type="submit" disabled={busy || !classrooms.length}>Enviar comunicado</button>
      </form>

      <section className="panel teacher-announcements-operations">
        <header><span>OPERAÇÃO</span><h2>Processamentos recentes</h2><p>Conclusões, falhas e solicitações relacionadas às tarefas internas do EduCode.</p></header>
        <div className="card-list">{items.length ? items.map((item) => <article className={`compact-card ${item.status === 'unread' ? 'unread-card' : ''}`} key={item.id}><strong>{item.title}</strong><span>{item.message}</span><small>{new Date(item.created_at).toLocaleString('pt-BR')}</small><div className="button-row"><Link className="secondary-button" to={item.action_path ?? `/tarefas/${item.job_id}`}>Abrir tarefa</Link>{item.status === 'unread' ? <button type="button" onClick={() => void markRead(item.id)}>Marcar como lida</button> : null}</div></article>) : <p>Nenhuma notificação operacional.</p>}</div>
      </section>
    </div>
  </section>
}
