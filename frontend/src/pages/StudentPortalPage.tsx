import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { animeStudioApi } from '../features/animeStudio/api'
import type { AnimePublicationLibraryItem } from '../features/animeStudio/types'
import { comicReaderApi } from '../features/comicReaderAccess/api'
import type { ReaderRelease } from '../features/comicReaderAccess/types'
import { api } from '../lib/api'
import type { StudentOwnProgress } from '../types/analytics'
import type { NotificationItem, StudentAssignmentCard } from '../types/delivery'
import './studentPortal.css'

interface PortalState {
  assignments: StudentAssignmentCard[]
  notifications: NotificationItem[]
  progress: StudentOwnProgress | null
  comics: ReaderRelease[]
  animes: AnimePublicationLibraryItem[]
}

const initialState: PortalState = {
  assignments: [],
  notifications: [],
  progress: null,
  comics: [],
  animes: [],
}

function dueLabel(value?: string | null): string {
  if (!value) return 'Sem prazo definido'
  return `Até ${new Date(value).toLocaleDateString('pt-BR')}`
}

export function StudentPortalPage() {
  const [state, setState] = useState<PortalState>(initialState)
  const [loading, setLoading] = useState(true)
  const [unavailable, setUnavailable] = useState<string[]>([])

  useEffect(() => {
    let active = true
    const requests = [
      api<StudentAssignmentCard[]>('/student/assignments'),
      api<NotificationItem[]>('/student/notifications'),
      api<StudentOwnProgress>('/analytics/student/progress'),
      comicReaderApi.releases(),
      animeStudioApi.listPublications(),
    ] as const

    void Promise.allSettled(requests).then((results) => {
      if (!active) return
      const failed: string[] = []
      const value = <T,>(index: number, fallback: T, label: string): T => {
        const result = results[index]
        if (result.status === 'fulfilled') return result.value as T
        failed.push(label)
        return fallback
      }
      setState({
        assignments: value(0, [], 'atividades'),
        notifications: value(1, [], 'notificações'),
        progress: value(2, null, 'progresso'),
        comics: value(3, [], 'HQs'),
        animes: value(4, [], 'animes'),
      })
      setUnavailable(failed)
      setLoading(false)
    })

    return () => { active = false }
  }, [])

  const pending = useMemo(
    () => state.assignments.filter((item) => item.progress_status !== 'completed'),
    [state.assignments],
  )
  const unread = state.notifications.filter((item) => item.status === 'unread')

  return (
    <section className="student-portal" aria-busy={loading}>
      <header className="student-portal-hero">
        <div>
          <span className="eyebrow">MINHA JORNADA</span>
          <h1>Olá! O que vamos aprender hoje?</h1>
          <p>Continue atividades, leia HQs, assista aos vídeos da turma e acompanhe sua evolução em um só lugar.</p>
        </div>
        <Link className="student-portal-primary" to="/aluno/atividades">Ver minhas atividades</Link>
      </header>

      {loading ? <div className="student-portal-status" role="status">Carregando sua jornada…</div> : null}
      {unavailable.length ? <div className="student-portal-warning" role="alert">Algumas informações não puderam ser carregadas agora: {unavailable.join(', ')}.</div> : null}

      {!loading ? <>
        <section className="student-portal-metrics" aria-label="Resumo da aprendizagem">
          <article><span>Para continuar</span><strong>{pending.length}</strong><small>atividade(s)</small></article>
          <article><span>Concluídas</span><strong>{state.progress?.completed_activities ?? 0}</strong><small>atividade(s)</small></article>
          <article><span>Minha média</span><strong>{state.progress?.average_percentage == null ? '—' : `${state.progress.average_percentage.toFixed(0)}%`}</strong><small>resultado pessoal</small></article>
          <article><span>Novidades</span><strong>{unread.length}</strong><small>não lida(s)</small></article>
        </section>

        <div className="student-portal-columns">
          <section className="student-portal-panel">
            <header><div><span>PRÓXIMOS PASSOS</span><h2>Continue aprendendo</h2></div><Link to="/aluno/atividades">Ver todas</Link></header>
            {pending.length ? <div className="student-portal-task-list">{pending.slice(0, 3).map((item) => <article key={item.id}><div><span>{item.assignment_type.replaceAll('_', ' ')}</span><h3>{item.title}</h3><p>{dueLabel(item.due_at)}</p></div><Link to={`/aluno/atividades/${item.id}`}>{item.progress_status === 'in_progress' ? 'Continuar' : 'Começar'}</Link></article>)}</div> : <p className="student-portal-empty">Você não tem atividades pendentes.</p>}
          </section>

          <aside className="student-portal-panel student-portal-news">
            <header><div><span>ATUALIZAÇÕES</span><h2>Notificações</h2></div></header>
            {state.notifications.length ? state.notifications.slice(0, 4).map((item) => <article key={item.id} className={item.status === 'unread' ? 'is-unread' : ''}><i aria-hidden="true" /><div><strong>{item.title}</strong><p>{item.message}</p></div></article>) : <p className="student-portal-empty">Nenhuma notificação no momento.</p>}
          </aside>
        </div>

        <section className="student-portal-shelf">
          <header><div><span>BIBLIOTECA DA TURMA</span><h2>Conteúdos para você</h2></div></header>
          <div>
            {state.comics.slice(0, 3).map((item) => <Link to={`/comic-reader/releases/${item.id}`} key={item.id}><span aria-hidden="true">▤</span><div><small>HQ INTERATIVA</small><strong>{item.release_name}</strong><p>Continuar leitura</p></div></Link>)}
            {state.animes.slice(0, 3).map((item) => <Link to="/anime-library" key={item.publication.project_id}><span aria-hidden="true">▶</span><div><small>VÍDEO DA TURMA</small><strong>{item.publication.title}</strong><p>Assistir agora</p></div></Link>)}
            {!state.comics.length && !state.animes.length ? <p className="student-portal-empty">Novas HQs e vídeos publicados aparecerão aqui.</p> : null}
          </div>
        </section>

        <nav className="student-portal-shortcuts" aria-label="Atalhos da área do estudante">
          <Link to="/aluno/portfolio"><span aria-hidden="true">◆</span><strong>Meu portfólio</strong><small>Evidências e competências</small></Link>
          <Link to="/aluno/progresso"><span aria-hidden="true">↗</span><strong>Meu progresso</strong><small>Resultados e próximos desafios</small></Link>
          <Link to="/aluno/minha-trilha"><span aria-hidden="true">⌁</span><strong>Minha trilha</strong><small>Objetivos personalizados</small></Link>
          <Link to="/student/assessments"><span aria-hidden="true">✓</span><strong>Avaliações</strong><small>Atividades avaliativas disponíveis</small></Link>
          <Link to="/student/interventions"><span aria-hidden="true">✚</span><strong>Meu apoio</strong><small>Planos e orientações do professor</small></Link>
        </nav>
      </> : null}
    </section>
  )
}
