import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  schoolAdmissionsApi,
  type AdmissionsDashboard,
} from '../features/schoolAdmissions/api'

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
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState('')

  useEffect(() => {
    void schoolAdmissionsApi.dashboard()
      .then(setDashboard)
      .catch((error: unknown) => setNotice(
        error instanceof Error ? error.message : 'Não foi possível carregar o painel.',
      ))
      .finally(() => setLoading(false))
  }, [])

  return <main className="school-secretariat-module" aria-busy={loading}>
    <div className="school-secretariat-heading">
      <div><span>VISÃO GERAL</span><h2>Dashboard da Secretaria</h2></div>
      <p>Acompanhe o fluxo e abra cada área sem misturar tarefas.</p>
    </div>
    <p className="school-secretariat-notice" aria-live="polite">{notice}</p>
    <div className="school-secretariat-metrics">
      <article><strong>{dashboard.submitted}</strong><span>Enviadas</span></article>
      <article><strong>{dashboard.under_review}</strong><span>Em análise</span></article>
      <article><strong>{dashboard.waitlisted}</strong><span>Na fila</span></article>
      <article><strong>{dashboard.approved}</strong><span>Aprovadas</span></article>
    </div>
    <div className="school-secretariat-module-grid">
      <Link to="/secretaria/matriculas"><strong>Matrículas</strong><span>Analise inscrições e aprove vínculos.</span></Link>
      <Link to="/secretaria/documentos"><strong>Documentos</strong><span>Configure checklist, versões e análise.</span></Link>
      <Link to="/secretaria/turmas-vagas"><strong>Turmas e vagas</strong><span>Gerencie unidades, lotação e reservas.</span></Link>
    </div>
  </main>
}
