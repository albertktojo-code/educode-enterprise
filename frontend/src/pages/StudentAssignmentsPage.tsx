import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'
import type { NotificationItem, StudentAssignmentCard } from '../types/delivery'

export function StudentAssignmentsPage() {
  const [assignments, setAssignments] = useState<StudentAssignmentCard[]>([])
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [filter, setFilter] = useState<'all' | 'not_started' | 'in_progress' | 'completed'>('all')
  const [message, setMessage] = useState('')

  async function load() {
    const [assignmentData, notificationData] = await Promise.all([
      api<StudentAssignmentCard[]>('/student/assignments'),
      api<NotificationItem[]>('/student/notifications'),
    ])
    setAssignments(assignmentData); setNotifications(notificationData)
  }
  useEffect(() => { void load().catch((error: Error) => setMessage(error.message)) }, [])
  const visible = assignments.filter((item) => filter === 'all' || item.progress_status === filter)

  return <section className="student-home">
    <header className="student-hero"><div><span className="eyebrow">MINHA APRENDIZAGEM</span><h1>Minhas atividades</h1><p>Continue de onde parou, acompanhe prazos e consulte seus resultados.</p></div><div className="student-summary"><strong>{assignments.filter((item) => item.progress_status === 'not_started').length}</strong><span>para fazer</span></div></header>
    {message ? <div className="inline-message">{message}</div> : null}
    <div className="student-filter-row">{(['all','not_started','in_progress','completed'] as const).map((item) => <button className={filter === item ? 'active' : ''} onClick={() => setFilter(item)} key={item}>{item === 'all' ? 'Todas' : item === 'not_started' ? 'Para fazer' : item === 'in_progress' ? 'Em andamento' : 'Concluídas'}</button>)}</div>
    <div className="student-layout"><div className="student-assignment-grid">{visible.map((item) => <article className={`student-assignment-card progress-${item.progress_status}`} key={item.id}><div className="student-card-top"><span>{item.assignment_type.replace('_',' ')}</span><strong>{item.progress_status.replace('_',' ')}</strong></div><h2>{item.title}</h2><p>{item.due_at ? `Prazo: ${new Date(item.due_at).toLocaleString('pt-BR')}` : 'Sem prazo definido'}</p><div className="student-card-meta"><span>{item.attempts_used}/{item.maximum_attempts} tentativa(s)</span><span>{item.time_limit_minutes ? `${item.time_limit_minutes} min` : 'Sem limite'}</span></div>{item.best_percentage != null ? <div className="score-pill">Melhor resultado: {item.best_percentage}%</div> : null}<Link to={`/aluno/atividades/${item.id}`}>{item.progress_status === 'in_progress' ? 'Continuar' : item.progress_status === 'completed' ? 'Ver atividade' : 'Abrir'}</Link></article>)}{!visible.length ? <p className="muted">Nenhuma atividade nesta categoria.</p> : null}</div>
    <aside className="panel notification-panel"><h2>Notificações</h2>{notifications.slice(0,8).map((item) => <article key={item.id} className={item.status === 'unread' ? 'notification unread' : 'notification'}><strong>{item.title}</strong><p>{item.message}</p><small>{new Date(item.created_at).toLocaleString('pt-BR')}</small></article>)}{!notifications.length ? <p className="muted">Nenhuma notificação.</p> : null}</aside></div>
  </section>
}
