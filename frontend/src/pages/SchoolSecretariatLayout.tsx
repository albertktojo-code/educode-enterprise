import { NavLink, Outlet } from 'react-router-dom'

import './schoolSecretariat.css'

const modules = [
  { to: '/secretaria', label: 'Dashboard', end: true },
  { to: '/secretaria/matriculas', label: 'Matrículas' },
  { to: '/secretaria/documentos', label: 'Documentos' },
  { to: '/secretaria/turmas-vagas', label: 'Turmas e vagas' },
]

export function SchoolSecretariatLayout() {
  return <section className="school-secretariat">
    <header className="school-secretariat-hero">
      <div>
        <span>EDUCODE SECRETARIA</span>
        <h1>Secretaria Digital</h1>
        <p>Módulos administrativos separados, seguros e conectados ao núcleo educacional.</p>
      </div>
    </header>
    <nav className="school-secretariat-tabs" aria-label="Módulos da Secretaria">
      {modules.map((item) => <NavLink
        key={item.to}
        to={item.to}
        end={item.end}
        className={({ isActive }) => isActive ? 'active' : undefined}
      >{item.label}</NavLink>)}
    </nav>
    <Outlet />
  </section>
}
