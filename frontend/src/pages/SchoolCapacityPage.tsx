import { useEffect, useState, type FormEvent } from 'react'

import { schoolAdmissionsApi, type CapacitySnapshot, type SchoolUnit } from '../features/schoolAdmissions/api'
import type { Classroom } from '../types/education'

export function SchoolCapacityPage() {
  const [units, setUnits] = useState<SchoolUnit[]>([])
  const [classrooms, setClassrooms] = useState<Classroom[]>([])
  const [capacities, setCapacities] = useState<CapacitySnapshot[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')

  async function load() {
    const [dashboard, unitItems, classroomItems] = await Promise.all([
      schoolAdmissionsApi.dashboard(), schoolAdmissionsApi.units(), schoolAdmissionsApi.classrooms(),
    ])
    setCapacities(dashboard.capacities)
    setUnits(unitItems.filter((item) => item.is_active))
    setClassrooms(classroomItems.filter((item) => item.is_active))
  }

  useEffect(() => {
    void load().catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'Não foi possível carregar turmas e vagas.')).finally(() => setLoading(false))
  }, [])

  async function submitUnit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const values = new FormData(form)
    setBusy(true)
    try {
      await schoolAdmissionsApi.createUnit({ name: String(values.get('name') ?? ''), code: String(values.get('code') ?? '') })
      form.reset(); setNotice('Unidade escolar criada.'); await load()
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Não foi possível criar a unidade.') } finally { setBusy(false) }
  }

  async function submitCapacity(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    const classroomId = String(values.get('classroom_id') ?? '')
    setBusy(true)
    try {
      await schoolAdmissionsApi.placeClassroom(classroomId, String(values.get('school_unit_id') ?? ''), String(values.get('shift') ?? ''))
      await schoolAdmissionsApi.configureCapacity(classroomId, { maximum_seats: Number(values.get('maximum_seats')), reservation_duration_minutes: Number(values.get('reservation_duration_minutes')), waitlist_enabled: true })
      setNotice('Turma e capacidade atualizadas.'); await load()
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Não foi possível configurar a turma.') } finally { setBusy(false) }
  }

  return <main className="school-secretariat-module" aria-busy={loading}>
    <div className="school-secretariat-heading"><div><span>TURMAS E VAGAS</span><h2>Capacidade escolar</h2></div><p>Unidades, turnos, lotação e reservas.</p></div>
    <p className="school-secretariat-notice" aria-live="polite">{notice}</p>
    <div className="school-secretariat-columns">
      <form className="panel" onSubmit={(event) => void submitUnit(event)}><h3>Nova unidade</h3><label htmlFor="unit-name">Nome<input id="unit-name" name="name" minLength={2} maxLength={160} required /></label><label htmlFor="unit-code">Código<input id="unit-code" name="code" pattern="[A-Za-z0-9_-]+" required /></label><button disabled={busy}>Criar unidade</button></form>
      <form className="panel" onSubmit={(event) => void submitCapacity(event)}><h3>Configurar turma</h3><label htmlFor="capacity-unit">Unidade<select id="capacity-unit" name="school_unit_id" required><option value="">Selecione</option>{units.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}</select></label><label htmlFor="capacity-classroom">Turma<select id="capacity-classroom" name="classroom_id" required><option value="">Selecione</option>{classrooms.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label htmlFor="capacity-shift">Turno<select id="capacity-shift" name="shift"><option value="morning">Manhã</option><option value="afternoon">Tarde</option><option value="evening">Noite</option><option value="full_time">Integral</option></select></label><label htmlFor="maximum-seats">Capacidade<input id="maximum-seats" name="maximum_seats" type="number" min={1} max={500} defaultValue={30} /></label><label htmlFor="reservation-duration">Reserva (minutos)<input id="reservation-duration" name="reservation_duration_minutes" type="number" min={5} max={10080} defaultValue={1440} /></label><button disabled={busy}>Salvar configuração</button></form>
    </div>
    <section className="panel"><h3>Ocupação</h3>{capacities.length ? <div className="school-secretariat-capacities">{capacities.map((item) => <article key={item.classroom_id}><strong>{item.classroom_name}</strong><span>{item.occupied_seats} matriculados · {item.reserved_seats} reservados</span><b>{item.available_seats} vaga(s)</b><small>Fila: {item.waitlist_size}</small></article>)}</div> : <p>Nenhuma capacidade configurada.</p>}</section>
  </main>
}
