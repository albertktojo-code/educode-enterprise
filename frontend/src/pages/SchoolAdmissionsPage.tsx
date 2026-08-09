import { useEffect, useState } from 'react'

import {
  schoolAdmissionsApi,
  type EnrollmentApplication,
} from '../features/schoolAdmissions/api'

export function SchoolAdmissionsPage() {
  const [applications, setApplications] = useState<EnrollmentApplication[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')

  async function load() {
    const dashboard = await schoolAdmissionsApi.dashboard()
    setApplications(dashboard.applications)
  }

  useEffect(() => {
    void load()
      .catch((error: unknown) => setNotice(
        error instanceof Error ? error.message : 'Não foi possível carregar as matrículas.',
      ))
      .finally(() => setLoading(false))
  }, [])

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

  return <main className="school-secretariat-module" aria-busy={loading}>
    <div className="school-secretariat-heading">
      <div><span>MATRÍCULAS</span><h2>Pré-matrículas</h2></div>
      <p>Reservas, fila de espera e aprovação em uma área dedicada.</p>
    </div>
    <p className="school-secretariat-notice" aria-live="polite">{notice}</p>
    <section className="panel">
      {applications.length ? <div className="school-secretariat-table" role="region" aria-label="Pré-matrículas" tabIndex={0}>
        <table><thead><tr><th>Estudante</th><th>Unidade</th><th>Turma</th><th>Status</th><th>Ações</th></tr></thead>
          <tbody>{applications.map((item) => <tr key={item.id}>
            <td>{item.student_name}</td><td>{item.school_unit_name}</td><td>{item.classroom_name}</td><td>{item.status}</td>
            <td><button type="button" disabled={busy} onClick={() => void act(item.id, 'reserve')}>Reservar</button>
              <button type="button" disabled={busy} onClick={() => void act(item.id, 'approve')}>Aprovar</button></td>
          </tr>)}</tbody></table>
      </div> : <p>{loading ? 'Carregando matrículas…' : 'Nenhuma pré-matrícula recebida.'}</p>}
    </section>
  </main>
}
