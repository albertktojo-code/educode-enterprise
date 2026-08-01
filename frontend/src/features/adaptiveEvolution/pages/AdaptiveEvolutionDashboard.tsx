import { NavLink } from "react-router-dom";
import { ModuleCard } from "../components/ModuleCard";
import "../styles.css";

const modules = [
  ["Pistas graduais", "Ajuda progressiva por tentativa, tempo, erro e acessibilidade.", "hints"],
  ["Revisão espaçada", "Agenda individual de revisão com intervalos explicáveis.", "reviews"],
  ["Feedback adaptado", "Mensagens ajustadas ao erro, domínio e uso de pistas.", "feedback"],
  ["Dificuldade individual", "Nível de desafio por estudante e habilidade.", "difficulty"],
  ["Regras de avanço", "Critérios configuráveis, versionados e auditáveis.", "progression"],
  ["Versões acessíveis", "Geração automática vinculada ao recurso original.", "accessibility"],
] as const;

export function AdaptiveEvolutionDashboard() {
  return (
    <main className="ae-page">
      <div className="ae-hero">
        <div>
          <span className="ae-kicker">EduCode Enterprise 2.0 · Sprint 14.1</span>
          <h1>Adaptação pedagógica e acessibilidade</h1>
          <p>
            Evolução pós-Sprint 14 com decisões determinísticas, explicáveis, versionadas e sujeitas à revisão docente.
          </p>
        </div>
      </div>

      <div className="ae-grid">
        {modules.map(([title, description, path]) => (
          <ModuleCard key={path} title={title} description={description}>
            <NavLink className="ae-button ae-button--secondary" to={`/teacher/adaptive-evolution/${path}`}>
              Abrir módulo
            </NavLink>
          </ModuleCard>
        ))}
      </div>
    </main>
  );
}
