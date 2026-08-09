import { useEffect, useMemo, useState, type FormEvent } from 'react'

import { EmptyState } from '../components/EmptyState'
import { LoadingState } from '../components/LoadingState'
import { credentialsApi } from '../features/credentials/api'
import type { CertificateStudent, PortfolioCertificate, PortfolioEvidence } from '../features/credentials/types'
import './teacherCertificates.css'

function formatDate(value: string | null): string {
  return value ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium' }).format(new Date(value)) : 'Data não informada'
}

export function TeacherCertificatesPage() {
  const [students, setStudents] = useState<CertificateStudent[]>([])
  const [studentId, setStudentId] = useState('')
  const [evidence, setEvidence] = useState<PortfolioEvidence[]>([])
  const [certificates, setCertificates] = useState<PortfolioCertificate[]>([])
  const [selectedEvidence, setSelectedEvidence] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingStudent, setLoadingStudent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')

  useEffect(() => {
    let active = true
    void credentialsApi.students()
      .then((items) => {
        if (!active) return
        setStudents(items)
        setStudentId(items[0]?.id ?? '')
      })
      .catch((error: unknown) => {
        if (active) setNotice(error instanceof Error ? error.message : 'Não foi possível carregar os estudantes.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!studentId) {
      setEvidence([])
      setCertificates([])
      return
    }
    let active = true
    setLoadingStudent(true)
    setSelectedEvidence([])
    setNotice('')
    void Promise.all([
      credentialsApi.evidence(studentId),
      credentialsApi.certificates(studentId),
    ]).then(([entries, issued]) => {
      if (!active) return
      setEvidence(entries)
      setCertificates(issued)
    }).catch((error: unknown) => {
      if (active) setNotice(error instanceof Error ? error.message : 'Não foi possível carregar o portfólio selecionado.')
    }).finally(() => { if (active) setLoadingStudent(false) })
    return () => { active = false }
  }, [studentId])

  const activeCertificates = useMemo(
    () => certificates.filter((certificate) => certificate.status === 'active').length,
    [certificates],
  )

  function toggleEvidence(id: string) {
    setSelectedEvidence((current) => current.includes(id)
      ? current.filter((item) => item !== id)
      : [...current, id])
  }

  async function issueCertificate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!studentId || !selectedEvidence.length) {
      setNotice('Selecione ao menos uma evidência antes de emitir o certificado.')
      return
    }
    const form = event.currentTarget
    const values = new FormData(form)
    setBusy(true)
    setNotice('')
    try {
      const certificate = await credentialsApi.issue({
        student_user_id: studentId,
        title: String(values.get('title') ?? ''),
        description: String(values.get('description') ?? ''),
        evidence_entry_ids: selectedEvidence,
      })
      setCertificates((current) => [certificate, ...current])
      setSelectedEvidence([])
      form.reset()
      setNotice('Certificado emitido e disponibilizado no portfólio do estudante.')
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Não foi possível emitir o certificado.')
    } finally {
      setBusy(false)
    }
  }

  async function revokeCertificate(certificateId: string, form: HTMLFormElement) {
    const reason = String(new FormData(form).get('reason') ?? '')
    setBusy(true)
    setNotice('')
    try {
      const certificate = await credentialsApi.revoke(certificateId, reason)
      setCertificates((current) => current.map((item) => item.id === certificate.id ? certificate : item))
      form.reset()
      setNotice('Certificado revogado. O histórico e o motivo foram preservados.')
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Não foi possível revogar o certificado.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="teacher-certificates" aria-busy={loading || loadingStudent}>
      <header className="teacher-certificates-hero">
        <div><span>EDUCODE CREDENTIALS</span><h1>Certificados por evidências</h1><p>Reconheça conquistas a partir da curadoria real do portfólio de cada estudante.</p></div>
        <label htmlFor="certificate-student">Estudante<select id="certificate-student" value={studentId} onChange={(event) => setStudentId(event.target.value)} disabled={loading || !students.length}><option value="">Selecione um estudante</option>{students.map((student) => <option key={student.id} value={student.id}>{student.full_name} · {student.email}</option>)}</select></label>
      </header>

      {loading ? <LoadingState label="Carregando estudantes" rows={3} /> : null}
      <p className="teacher-certificates-notice" aria-live="polite">{notice}</p>
      {!loading && !students.length ? <EmptyState icon="activity" title="Nenhum estudante disponível" description="Estudantes ativos da organização aparecerão aqui para emissão de certificados." /> : null}

      {studentId ? <>
        <section className="teacher-certificates-summary" aria-label="Resumo do estudante">
          <article><span>Evidências no portfólio</span><strong>{evidence.length}</strong></article>
          <article><span>Certificados ativos</span><strong>{activeCertificates}</strong></article>
          <article><span>Evidências selecionadas</span><strong>{selectedEvidence.length}</strong></article>
        </section>

        <div className="teacher-certificates-grid">
          <section className="teacher-certificates-panel">
            <header><span>1 · SELECIONE</span><h2>Evidências da aprendizagem</h2></header>
            {loadingStudent ? <LoadingState label="Carregando portfólio" rows={3} /> : evidence.length ? <div className="teacher-certificates-evidence">
              {evidence.map((item) => <label key={item.id} className={selectedEvidence.includes(item.id) ? 'selected' : ''}><input type="checkbox" checked={selectedEvidence.includes(item.id)} onChange={() => toggleEvidence(item.id)} /><span><strong>{item.title_snapshot}</strong><small>{item.assignment_type_snapshot.replaceAll('_', ' ')} · {item.percentage_snapshot.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%</small>{item.reflection ? <p>“{item.reflection}”</p> : null}</span></label>)}
            </div> : <EmptyState icon="activity" title="Sem evidências selecionadas" description="O estudante precisa adicionar atividades concluídas à curadoria do portfólio." />}
          </section>

          <form className="teacher-certificates-panel teacher-certificates-form" onSubmit={(event) => void issueCertificate(event)}>
            <header><span>2 · EMITA</span><h2>Novo certificado</h2></header>
            <label htmlFor="certificate-title">Título<input id="certificate-title" name="title" minLength={3} maxLength={240} required placeholder="Ex.: Destaque em pensamento computacional" /></label>
            <label htmlFor="certificate-description">Descrição<textarea id="certificate-description" name="description" maxLength={2000} rows={5} placeholder="Descreva a conquista reconhecida." /></label>
            <small>O certificado receberá um código único e ficará visível no portfólio do estudante.</small>
            <button type="submit" disabled={busy || !selectedEvidence.length}>Emitir certificado</button>
          </form>
        </div>

        <section className="teacher-certificates-panel teacher-certificates-history">
          <header><span>HISTÓRICO</span><h2>Certificados emitidos</h2></header>
          {certificates.length ? <div>{certificates.map((certificate) => <article key={certificate.id}>
            <div className="teacher-certificates-card-heading"><div><small>{certificate.status === 'active' ? 'ATIVO' : 'REVOGADO'} · {formatDate(certificate.issued_at)}</small><h3>{certificate.title}</h3><p>{certificate.description || 'Sem descrição.'}</p></div><div><code>{certificate.verification_code}</code><a href={`/credentials/verificar/${certificate.verification_code}`} target="_blank" rel="noreferrer">Abrir certificado</a></div></div>
            <small>{certificate.evidence_entry_ids.length} evidência(s) vinculada(s)</small>
            {certificate.status === 'active' ? <form onSubmit={(event) => { event.preventDefault(); void revokeCertificate(certificate.id, event.currentTarget) }}><label htmlFor={`reason-${certificate.id}`}>Motivo da revogação<input id={`reason-${certificate.id}`} name="reason" minLength={3} maxLength={300} required /></label><button type="submit" disabled={busy}>Revogar certificado</button></form> : <p className="teacher-certificates-revoked">Revogado em {formatDate(certificate.revoked_at)} · {certificate.revocation_reason}</p>}
          </article>)}</div> : <EmptyState icon="activity" title="Nenhum certificado emitido" description="Selecione evidências e emita o primeiro reconhecimento deste estudante." />}
        </section>
      </> : null}
    </section>
  )
}
