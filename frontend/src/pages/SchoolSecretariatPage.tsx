import { useEffect, useState, type FormEvent } from 'react'

import {
  schoolAdmissionsApi,
  type AdmissionsDashboard,
  type SchoolUnit,
} from '../features/schoolAdmissions/api'
import type { Classroom } from '../types/education'
import './schoolSecretariat.css'

const emptyDashboard: AdmissionsDashboard = {
  applications: [],
  capacities: [],
  submitted: 0,
  under_review: 0,
  waitlisted: 0,
  approved: 0,
}

export function SchoolSecretariatPage() {
  const [dashboard, setDashboard] = useState(emptyDashboard)
  const [units, setUnits] = useState<SchoolUnit[]>([])
  const [classrooms, setClassrooms] = useState<Classroom[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')

  async function load() {
    const [summary, unitItems, classroomItems] = await Promise.all([
      schoolAdmissionsApi.dashboard(),
      schoolAdmissionsApi.units(),
      schoolAdmissionsApi.classrooms(),
    ])
    setDashboard(summary)
    setUnits(unitItems.filter((item) => item.is_active))
    setClassrooms(classroomItems.filter((item) => item.is_active))
  }

  useEffect(() => {
    void load()
      .catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'Não foi possível carregar a Secretaria.'))
      .finally(() => setLoading(false))
  }, [])

  async function submitUnit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const values = new FormData(form)
    setBusy(true)
    try {
      await schoolAdmissionsApi.createUnit({
        name: String(values.get('name') ?? ''),
        code: String(values.get('code') ?? ''),
      })
      form.reset()
      setNotice('Unidade escolar criada.')
      await load()
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Não foi possível criar a unidade.')
    } finally {
      setBusy(false)
    }
  }

  async function submitCapacity(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const values = new FormData(form)
    const classroomId = String(values.get('classroom_id') ?? '')
    const unitId = String(values.get('school_unit_id') ?? '')
    setBusy(true)
    try {
      await schoolAdmissionsApi.placeClassroom(
        classroomId,
        unitId,
        String(values.get('shift') ?? ''),
      )
      await schoolAdmissionsApi.configureCapacity(classroomId, {
        maximum_seats: Number(values.get('maximum_seats')),
        reservation_duration_minutes: Number(values.get('reservation_duration_minutes')),
        waitlist_enabled: true,
      })
      setNotice('Turma vinculada à unidade e capacidade atualizada.')
      await load()
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Não foi possível configurar a turma.')
    } finally {
      setBusy(false)
    }
  }

  async function act(applicationId: string, action: 'reserve' | 'approve') {
    setBusy(true)
    try {
      await schoolAdmissionsApi[action](applicationId)
      setNotice(action === 'reserve' ? 'Reserva ou fila atualizada.' : 'Matrícula aprovada.')
      await load()
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Não foi possível concluir a ação.')
    } finally {
      setBusy(false)
    }
  }

  return <section className="school-secretariat" aria-busy={loading}>
    <header className="school-secretariat-hero"><div><span>EDUCODE SECRETARIA</span><h1>Matrículas e vagas</h1><p>Organize unidades, capacidade das turmas, reservas e fila de espera com isolamento institucional.</p></div></header>
    <p className="school-secretariat-notice" aria-live="polite">{notice}</p>
    <div className="school-secretariat-metrics">
      <article><strong>{dashboard.submitted}</strong><span>Enviadas</span></article>
      <article><strong>{dashboard.under_review}</strong><span>Em análise</span></article>
      <article><strong>{dashboard.waitlisted}</strong><span>Na fila</span></article>
      <article><strong>{dashboard.approved}</strong><span>Aprovadas</span></article>
    </div>
    <div className="school-secretariat-columns">
      <form className="panel" onSubmit={(event) => void submitUnit(event)}>
        <h2>Nova unidade</h2>
        <label htmlFor="unit-name">Nome<input id="unit-name" name="name" minLength={2} maxLength={160} required /></label>
        <label htmlFor="unit-code">Código<input id="unit-code" name="code" minLength={2} maxLength={40} pattern="[A-Za-z0-9_-]+" required /></label>
        <button type="submit" disabled={busy}>Criar unidade</button>
      </form>
      <form className="panel" onSubmit={(event) => void submitCapacity(event)}>
        <h2>Configurar turma e vagas</h2>
        <label htmlFor="capacity-unit">Unidade<select id="capacity-unit" name="school_unit_id" required><option value="">Selecione</option>{units.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}</select></label>
        <label htmlFor="capacity-classroom">Turma<select id="capacity-classroom" name="classroom_id" required><option value="">Selecione</option>{classrooms.map((classroom) => <option key={classroom.id} value={classroom.id}>{classroom.name}</option>)}</select></label>
        <label htmlFor="capacity-shift">Turno<select id="capacity-shift" name="shift" required><option value="morning">Manhã</option><option value="afternoon">Tarde</option><option value="evening">Noite</option><option value="full_time">Integral</option></select></label>
        <label htmlFor="maximum-seats">Capacidade<input id="maximum-seats" name="maximum_seats" type="number" min={1} max={500} defaultValue={30} required /></label>
        <label htmlFor="reservation-duration">Reserva (minutos)<input id="reservation-duration" name="reservation_duration_minutes" type="number" min={5} max={10080} defaultValue={1440} required /></label>
        <button type="submit" disabled={busy || !units.length || !classrooms.length}>Salvar configuração</button>
      </form>
    </div>
    <section className="panel"><h2>Ocupação das turmas</h2>{dashboard.capacities.length ? <div className="school-secretariat-capacities">{dashboard.capacities.map((item) => <article key={item.classroom_id}><strong>{item.classroom_name}</strong><span>{item.occupied_seats} matriculados · {item.reserved_seats} reservados</span><b>{item.available_seats} vaga(s) disponível(is)</b><small>Fila: {item.waitlist_size}</small></article>)}</div> : <p>Nenhuma capacidade configurada.</p>}</section>
    <section className="panel"><h2>Pré-matrículas recentes</h2>{dashboard.applications.length ? <div className="school-secretariat-table" role="region" aria-label="Pré-matrículas" tabIndex={0}><table><thead><tr><th>Estudante</th><th>Unidade</th><th>Turma</th><th>Status</th><th>Ações</th></tr></thead><tbody>{dashboard.applications.map((item) => <tr key={item.id}><td>{item.student_name}</td><td>{item.school_unit_name}</td><td>{item.classroom_name}</td><td>{item.status}</td><td><button type="button" disabled={busy} onClick={() => void act(item.id, 'reserve')}>Reservar</button><button type="button" disabled={busy} onClick={() => void act(item.id, 'approve')}>Aprovar</button></td></tr>)}</tbody></table></div> : <p>Nenhuma pré-matrícula recebida.</p>}</section>
  </section>
}
