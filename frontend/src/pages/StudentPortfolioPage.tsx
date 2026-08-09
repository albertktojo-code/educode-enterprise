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
import './studentPortfolioCuration.css'

interface PortfolioState {
  assignments: StudentAssignmentCard[]
  progress: StudentOwnProgress | null
  comics: ReaderRelease[]
  animes: AnimePublicationLibraryItem[]
  entries: PortfolioEntry[]
  productions: PortfolioProduction[]
  certificates: PortfolioCertificate[]
}

interface PortfolioCertificate { id: string; title: string; description: string; verification_code: string; status: string; issued_at: string; revoked_at: string | null; revocation_reason: string }

interface PortfolioProduction {
  id: string
  kind: 'project' | 'comic' | 'anime'
  title: string
  description: string
  status: string
  updated_at: string
  route: string
}

interface PortfolioEntry {
  id: string
  assignment_id: string
  attempt_id: string
  title_snapshot: string
  assignment_type_snapshot: string
  percentage_snapshot: number
  reflection: string
  revision: number
  completed_at_snapshot: string | null
}

const initialState: PortfolioState = {
  assignments: [],
  progress: null,
  comics: [],
  animes: [],
  entries: [],
  productions: [],
  certificates: [],
}

function percentage(value: number | null | undefined): string {
  return value == null ? 'Em análise' : `${value.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
}

export function StudentPortfolioPage() {
  const [state, setState] = useState<PortfolioState>(initialState)
  const [loading, setLoading] = useState(true)
  const [unavailable, setUnavailable] = useState<string[]>([])
  const [busyEntry, setBusyEntry] = useState<string | null>(null)
  const [notice, setNotice] = useState('')

  useEffect(() => {
    let active = true
    const requests = [
      api<StudentAssignmentCard[]>('/student/assignments'),
      api<StudentOwnProgress>('/analytics/student/progress'),
      comicReaderApi.releases(),
      animeStudioApi.listPublications(),
      api<PortfolioEntry[]>('/student/portfolio/entries'),
      api<PortfolioProduction[]>('/student/portfolio/productions'),
      api<PortfolioCertificate[]>('/student/portfolio/certificates'),
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
        entries: value(4, [], 'curadoria'),
        productions: value(5, [], 'produções autorais'),
        certificates: value(6, [], 'certificados'),
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
  const entriesByAssignment = useMemo(
    () => new Map(state.entries.map((entry) => [entry.assignment_id, entry])),
    [state.entries],
  )

  async function curateEvidence(assignmentId: string) {
    setBusyEntry(assignmentId)
    setNotice('')
    try {
      const entry = await api.post<PortfolioEntry>('/student/portfolio/entries', { assignment_id: assignmentId })
      setState((current) => ({
        ...current,
        entries: [entry, ...current.entries.filter((item) => item.id !== entry.id)],
      }))
      setNotice('Evidência adicionada ao seu portfólio.')
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Não foi possível adicionar a evidência.')
    } finally {
      setBusyEntry(null)
    }
  }

  async function saveReflection(entryId: string, reflection: string) {
    setBusyEntry(entryId)
    setNotice('')
    try {
      const entry = await api.patch<PortfolioEntry>(`/student/portfolio/entries/${entryId}`, { reflection })
      setState((current) => ({
        ...current,
        entries: current.entries.map((item) => item.id === entry.id ? entry : item),
      }))
      setNotice('Reflexão salva com autoria e histórico de revisão.')
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Não foi possível salvar a reflexão.')
    } finally {
      setBusyEntry(null)
    }
  }

  async function removeEvidence(entryId: string) {
    setBusyEntry(entryId)
    setNotice('')
    try {
      await api.delete<void>(`/student/portfolio/entries/${entryId}`)
      setState((current) => ({ ...current, entries: current.entries.filter((item) => item.id !== entryId) }))
      setNotice('Evidência removida da curadoria. O resultado original foi preservado.')
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Não foi possível remover a evidência.')
    } finally {
      setBusyEntry(null)
    }
  }

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
      <p className="student-portfolio-notice" aria-live="polite">{notice}</p>

      {!loading ? <>
        <section className="student-portfolio-metrics" aria-label="Resumo do portfólio">
          <article><span>Evidências selecionadas</span><strong>{state.entries.length}</strong></article>
          <article><span>Média pessoal</span><strong>{percentage(state.progress?.average_percentage)}</strong></article>
          <article><span>Competências em destaque</span><strong>{skills.length}</strong></article>
          <article><span>Conteúdos da jornada</span><strong>{state.comics.length + state.animes.length}</strong></article>
        </section>

        <section className="student-portfolio-panel student-portfolio-curation">
          <header><div><span>MINHA CURADORIA</span><h2>Evidências e reflexões autorais</h2></div></header>
          {state.entries.length ? <div className="student-portfolio-curated-list">
            {state.entries.map((entry) => <article key={entry.id}>
              <div className="student-portfolio-curated-heading">
                <div><span>{entry.assignment_type_snapshot.replaceAll('_', ' ')}</span><h3>{entry.title_snapshot}</h3></div>
                <strong>{percentage(entry.percentage_snapshot)}</strong>
              </div>
              <form onSubmit={(event) => {
                event.preventDefault()
                const reflection = String(new FormData(event.currentTarget).get('reflection') ?? '')
                void saveReflection(entry.id, reflection)
              }}>
                <label htmlFor={`reflection-${entry.id}`}>O que aprendi com esta experiência?</label>
                <textarea id={`reflection-${entry.id}`} name="reflection" maxLength={2000} rows={3} defaultValue={entry.reflection} disabled={busyEntry === entry.id} />
                <div><small>Revisão {entry.revision} · até 2.000 caracteres</small><button type="submit" disabled={busyEntry === entry.id}>Salvar reflexão</button><button type="button" className="danger" disabled={busyEntry === entry.id} onClick={() => void removeEvidence(entry.id)}>Remover da curadoria</button></div>
              </form>
            </article>)}
          </div> : <EmptyState icon="activity" title="Escolha suas melhores evidências" description="Use o botão nas atividades concluídas para começar sua curadoria e registrar o que aprendeu." />}
        </section>

        <section className="student-portfolio-panel student-portfolio-gallery">
          <header><div><span>MINHAS PRODUÇÕES</span><h2>Projetos autorais no EduCode Studio</h2></div></header>
          {state.productions.length ? <div>
            {state.productions.map((production) => <Link to={production.route} key={`${production.kind}-${production.id}`}><span aria-hidden="true">{production.kind === 'anime' ? '▶' : production.kind === 'comic' ? '▤' : '◆'}</span><small>{production.kind}</small><strong>{production.title}</strong><p>{production.description}</p><small>{production.status.replaceAll('_', ' ')}</small></Link>)}
          </div> : <EmptyState icon="folder" title="Nenhuma produção autoral ainda" description="Projetos, HQs e animes criados por você no EduCode aparecerão aqui sem copiar os arquivos de origem." />}
        </section>

        <section className="student-portfolio-panel student-portfolio-gallery">
          <header><div><span>CERTIFICADOS</span><h2>Conquistas verificáveis</h2></div></header>
          {state.certificates.length ? <div>{state.certificates.map((certificate) => <article key={certificate.id}><span aria-hidden="true">◆</span><small>{certificate.status === 'active' ? 'VÁLIDO' : 'REVOGADO'}</small><strong>{certificate.title}</strong><p>{certificate.description}</p><code>{certificate.verification_code}</code>{certificate.revocation_reason ? <small>{certificate.revocation_reason}</small> : null}</article>)}</div> : <EmptyState icon="activity" title="Nenhum certificado emitido" description="Certificados baseados em evidências aprovadas aparecerão aqui após emissão por um educador." />}
        </section>

        <div className="student-portfolio-columns">
          <section className="student-portfolio-panel">
            <header><div><span>EVIDÊNCIAS CANÔNICAS</span><h2>Atividades concluídas</h2></div><Link to="/aluno/atividades">Todas as atividades</Link></header>
            {completedAssignments.length ? <div className="student-portfolio-evidence-list">
              {completedAssignments.map((assignment) => <article key={assignment.id}>
                <div><span>{assignment.assignment_type.replaceAll('_', ' ')}</span><h3>{assignment.title}</h3><small>{assignment.attempts_used} tentativa(s) registrada(s)</small></div>
                <div><strong>{percentage(assignment.best_percentage)}</strong><Link to={`/aluno/atividades/${assignment.id}`}>Revisar evidência</Link>{entriesByAssignment.has(assignment.id) ? <small>Já está na curadoria</small> : <button type="button" disabled={busyEntry === assignment.id} onClick={() => void curateEvidence(assignment.id)}>Adicionar ao portfólio</button>}</div>
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
          <p>As evidências selecionadas referenciam resultados oficiais do EduCode e não alteram a atividade original. Suas reflexões são privadas nesta versão. Certificados serão adicionados quando houver regras próprias de emissão e revogação.</p>
        </aside>
      </> : null}
    </section>
  )
}
