import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { EmptyState } from '../components/EmptyState'
import { LoadingState } from '../components/LoadingState'
import { animeStudioApi } from '../features/animeStudio/api'
import type { AnimePublicationLibraryItem } from '../features/animeStudio/types'
import { comicReaderApi } from '../features/comicReaderAccess/api'
import type { ReaderRelease } from '../features/comicReaderAccess/types'
import { api } from '../lib/api'
import type { StudentOwnProgress } from '../types/analytics'
import type { StudentAssignmentCard } from '../types/delivery'
import './studentPortfolio.css'

interface PortfolioState {
  assignments: StudentAssignmentCard[]
  progress: StudentOwnProgress | null
  comics: ReaderRelease[]
  animes: AnimePublicationLibraryItem[]
}

const initialState: PortfolioState = {
  assignments: [],
  progress: null,
  comics: [],
  animes: [],
}

function percentage(value: number | null | undefined): string {
  return value == null ? 'Em análise' : `${value.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
}

export function StudentPortfolioPage() {
  const [state, setState] = useState<PortfolioState>(initialState)
  const [loading, setLoading] = useState(true)
  const [unavailable, setUnavailable] = useState<string[]>([])

  useEffect(() => {
    let active = true
    const requests = [
      api<StudentAssignmentCard[]>('/student/assignments'),
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
        progress: value(1, null, 'competências'),
        comics: value(2, [], 'HQs'),
        animes: value(3, [], 'vídeos'),
      })
      setUnavailable(failed)
      setLoading(false)
    })

    return () => { active = false }
  }, [])

  const completedAssignments = useMemo(
    () => state.assignments
      .filter((assignment) => assignment.progress_status === 'completed')
      .sort((left, right) => (right.best_percentage ?? -1) - (left.best_percentage ?? -1)),
    [state.assignments],
  )
  const skills = useMemo(() => {
    const rows = [...(state.progress?.strengths ?? []), ...(state.progress?.development_areas ?? [])]
    return [...new Map(rows.map((skill) => [
      `${skill.skill_code}-${skill.ct_pillar_code}`,
      skill,
    ])).values()].sort((left, right) => right.proficiency_score - left.proficiency_score)
  }, [state.progress])

  return (
    <section className="student-portfolio" aria-busy={loading}>
      <header className="student-portfolio-hero">
        <div>
          <span>EDUCODE CREDENTIALS</span>
          <h1>Meu portfólio de aprendizagem</h1>
          <p>Reúna evidências das atividades que você concluiu e acompanhe as competências construídas na sua jornada.</p>
        </div>
        <Link to="/aluno/progresso">Ver evolução detalhada</Link>
      </header>

      {loading ? <LoadingState label="Organizando seu portfólio" rows={4} /> : null}
      {unavailable.length ? <div className="student-portfolio-warning" role="alert">Algumas evidências não puderam ser carregadas agora: {unavailable.join(', ')}.</div> : null}

      {!loading ? <>
        <section className="student-portfolio-metrics" aria-label="Resumo do portfólio">
          <article><span>Evidências concluídas</span><strong>{completedAssignments.length}</strong></article>
          <article><span>Média pessoal</span><strong>{percentage(state.progress?.average_percentage)}</strong></article>
          <article><span>Competências em destaque</span><strong>{skills.length}</strong></article>
          <article><span>Conteúdos da jornada</span><strong>{state.comics.length + state.animes.length}</strong></article>
        </section>

        <div className="student-portfolio-columns">
          <section className="student-portfolio-panel">
            <header><div><span>EVIDÊNCIAS CANÔNICAS</span><h2>Atividades concluídas</h2></div><Link to="/aluno/atividades">Todas as atividades</Link></header>
            {completedAssignments.length ? <div className="student-portfolio-evidence-list">
              {completedAssignments.map((assignment) => <article key={assignment.id}>
                <div><span>{assignment.assignment_type.replaceAll('_', ' ')}</span><h3>{assignment.title}</h3><small>{assignment.attempts_used} tentativa(s) registrada(s)</small></div>
                <div><strong>{percentage(assignment.best_percentage)}</strong><Link to={`/aluno/atividades/${assignment.id}`}>Revisar evidência</Link></div>
              </article>)}
            </div> : <EmptyState icon="activity" title="Seu portfólio está começando" description="As atividades concluídas aparecerão aqui como evidências da sua aprendizagem." />}
          </section>

          <aside className="student-portfolio-panel">
            <header><div><span>COMPETÊNCIAS</span><h2>O que estou construindo</h2></div></header>
            {skills.length ? <ol className="student-portfolio-skills">
              {skills.map((skill) => <li key={`${skill.skill_code}-${skill.ct_pillar_code}`}>
                <div><strong>{skill.skill_code || skill.ct_pillar_code}</strong><span>{skill.evidence_count} evidência(s)</span></div>
                <progress max={100} value={skill.proficiency_score}>{skill.proficiency_score}%</progress>
                <b>{percentage(skill.proficiency_score)}</b>
              </li>)}
            </ol> : <EmptyState icon="activity" title="Competências em formação" description="Novas competências aparecerão após atividades com evidências suficientes." />}
          </aside>
        </div>

        <section className="student-portfolio-panel student-portfolio-gallery">
          <header><div><span>JORNADA MULTIMÍDIA</span><h2>HQs e vídeos disponíveis</h2></div></header>
          {state.comics.length || state.animes.length ? <div>
            {state.comics.map((comic) => <Link to={`/comic-reader/releases/${comic.id}`} key={comic.id}><span aria-hidden="true">▤</span><small>HQ</small><strong>{comic.release_name}</strong><p>Explorar publicação</p></Link>)}
            {state.animes.map((anime) => <Link to={`/anime-library?project=${anime.publication.project_id}`} key={anime.publication.project_id}><span aria-hidden="true">▶</span><small>VÍDEO</small><strong>{anime.publication.title}</strong><p>Assistir publicação</p></Link>)}
          </div> : <EmptyState icon="folder" title="Nenhum conteúdo disponível" description="HQs e vídeos autorizados pela sua turma aparecerão nesta jornada." />}
        </section>

        <aside className="student-portfolio-scope">
          <strong>Sobre este portfólio</strong>
          <p>Esta primeira versão reúne somente dados oficiais do EduCode. Reflexões autorais e certificados serão adicionados quando tiverem regras próprias de autoria, revisão e emissão.</p>
        </aside>
      </> : null}
    </section>
  )
}
