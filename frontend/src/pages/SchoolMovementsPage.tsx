import { type FormEvent, useEffect, useState } from 'react'

import {
  schoolAdmissionsApi,
  type ActiveEnrollment,
  type EnrollmentRenewal,
  type EnrollmentTransfer,
} from '../features/schoolAdmissions/api'
import type { Classroom } from '../types/education'

export function SchoolMovementsPage() {
  const [enrollments, setEnrollments] = useState<ActiveEnrollment[]>([])
  const [renewals, setRenewals] = useState<EnrollmentRenewal[]>([])
  const [transfers, setTransfers] = useState<EnrollmentTransfer[]>([])
  const [classrooms, setClassrooms] = useState<Classroom[]>([])
  const [transferType, setTransferType] = useState<'internal' | 'external'>('internal')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')

  async function load() {
    const [dashboard, classroomItems] = await Promise.all([
      schoolAdmissionsApi.movements(),
      schoolAdmissionsApi.classrooms(),
    ])
    setEnrollments(dashboard.enrollments)
    setRenewals(dashboard.renewals)
    setTransfers(dashboard.transfers)
    setClassrooms(classroomItems.filter((item) => item.is_active && item.school_unit_id))
  }

  useEffect(() => {
    void load().catch((error: unknown) => setNotice(
      error instanceof Error ? error.message : 'Não foi possível carregar as movimentações.',
    )).finally(() => setLoading(false))
  }, [])

  async function submitRenewal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setBusy(true)
    try {
      await schoolAdmissionsApi.createRenewal(String(data.get('enrollment_id')), {
        target_classroom_id: String(data.get('target_classroom_id')),
        target_academic_year: Number(data.get('target_academic_year')),
        reason: String(data.get('reason') ?? ''),
      })
      event.currentTarget.reset()
      setNotice('Solicitação de rematrícula criada.')
      await load()
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Não foi possível criar a rematrícula.')
    } finally { setBusy(false) }
  }

  async function submitTransfer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setBusy(true)
    try {
      await schoolAdmissionsApi.createTransfer(String(data.get('enrollment_id')), {
        transfer_type: transferType,
        destination_classroom_id: transferType === 'internal' ? String(data.get('destination_classroom_id')) : null,
        destination_name: transferType === 'external' ? String(data.get('destination_name')) : '',
        reason: String(data.get('reason')),
      })
      event.currentTarget.reset()
      setNotice('Solicitação de transferência criada.')
      await load()
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Não foi possível criar a transferência.')
    } finally { setBusy(false) }
  }

  async function review(kind: 'renewal' | 'transfer', id: string, decision: 'approved' | 'rejected') {
    const note = decision === 'rejected' ? window.prompt('Justificativa da rejeição:')?.trim() : ''
    if (decision === 'rejected' && !note) return
    setBusy(true)
    try {
      if (kind === 'renewal') await schoolAdmissionsApi.reviewRenewal(id, decision, note)
      else await schoolAdmissionsApi.reviewTransfer(id, decision, note)
      setNotice(decision === 'approved' ? 'Solicitação aprovada.' : 'Solicitação rejeitada.')
      await load()
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Não foi possível analisar a solicitação.')
    } finally { setBusy(false) }
  }

  return <main className="school-secretariat-module" aria-busy={loading}>
    <div className="school-secretariat-heading"><div><span>MOVIMENTAÇÕES</span><h2>Rematrículas e transferências</h2></div><p>Fluxos separados com histórico do vínculo e validação de vagas.</p></div>
    <p className="school-secretariat-notice" aria-live="polite">{notice}</p>
    <div className="school-secretariat-columns">
      <section className="panel"><h3>Nova rematrícula</h3><form onSubmit={submitRenewal}>
        <label>Estudante<select name="enrollment_id" required><option value="">Selecione</option>{enrollments.map((item) => <option key={item.id} value={item.id}>{item.student_name} · {item.classroom_name}</option>)}</select></label>
        <label>Turma de destino<select name="target_classroom_id" required><option value="">Selecione</option>{classrooms.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.school_year ?? 'ano não informado'}</option>)}</select></label>
        <label>Ano letivo<input name="target_academic_year" type="number" min="2020" max="2100" defaultValue={new Date().getFullYear() + 1} required /></label>
        <label>Observação<textarea name="reason" rows={2} /></label><button disabled={busy}>Solicitar rematrícula</button>
      </form></section>
      <section className="panel"><h3>Nova transferência</h3><form onSubmit={submitTransfer}>
        <label>Estudante<select name="enrollment_id" required><option value="">Selecione</option>{enrollments.map((item) => <option key={item.id} value={item.id}>{item.student_name} · {item.classroom_name}</option>)}</select></label>
        <label>Tipo<select value={transferType} onChange={(event) => setTransferType(event.target.value as 'internal' | 'external')}><option value="internal">Interna</option><option value="external">Externa</option></select></label>
        {transferType === 'internal' ? <label>Turma de destino<select name="destination_classroom_id" required><option value="">Selecione</option>{classrooms.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label> : <label>Instituição de destino<input name="destination_name" maxLength={180} required /></label>}
        <label>Motivo<textarea name="reason" minLength={3} rows={2} required /></label><button disabled={busy}>Solicitar transferência</button>
      </form></section>
    </div>
    <section className="panel"><h3>Rematrículas</h3><div className="school-secretariat-table"><table><thead><tr><th>Estudante</th><th>Origem</th><th>Destino</th><th>Ano</th><th>Status</th><th>Ações</th></tr></thead><tbody>{renewals.map((item) => <tr key={item.id}><td>{item.student_name}</td><td>{item.source_classroom_name}</td><td>{item.target_classroom_name}</td><td>{item.target_academic_year}</td><td>{item.status}</td><td>{item.status === 'submitted' && <><button disabled={busy} onClick={() => void review('renewal', item.id, 'approved')}>Aprovar</button><button disabled={busy} onClick={() => void review('renewal', item.id, 'rejected')}>Rejeitar</button></>}</td></tr>)}</tbody></table>{!renewals.length && <p>Nenhuma rematrícula solicitada.</p>}</div></section>
    <section className="panel"><h3>Transferências</h3><div className="school-secretariat-table"><table><thead><tr><th>Estudante</th><th>Origem</th><th>Destino</th><th>Tipo</th><th>Status</th><th>Ações</th></tr></thead><tbody>{transfers.map((item) => <tr key={item.id}><td>{item.student_name}</td><td>{item.source_classroom_name}</td><td>{item.destination_name}</td><td>{item.transfer_type === 'internal' ? 'Interna' : 'Externa'}</td><td>{item.status}</td><td>{item.status === 'submitted' && <><button disabled={busy} onClick={() => void review('transfer', item.id, 'approved')}>Aprovar</button><button disabled={busy} onClick={() => void review('transfer', item.id, 'rejected')}>Rejeitar</button></>}</td></tr>)}</tbody></table>{!transfers.length && <p>Nenhuma transferência solicitada.</p>}</div></section>
  </main>
}
