import { NavLink } from "react-router-dom";
import { ModuleCard } from "../components/ModuleCard";
import "../styles.css";

const modules = [
  ["Histórico de intervenções", "Recomendações explicáveis baseadas nos resultados das intervenções.", "interventions"],
  ["Eficácia dos materiais", "Indicadores descritivos de conclusão, acerto, ganho, tentativas e uso de pistas.", "materials"],
  ["Painel de trilhas", "Visão institucional consolidada de progresso, domínio e revisões atrasadas.", "paths"],
  ["Modelos versionados", "Configurações adaptativas imutáveis após publicação.", "models"],
  ["Simulação", "Teste de recomendações sem alterar dados pedagógicos reais.", "simulation"],
  ["Experimentos controlados", "Comparação descritiva de estratégias com atribuição estável.", "experiments"],
] as const;

export function AdaptiveInsightsDashboard() {
  return (
    <main className="ai-page">
      <header className="ai-hero">
        <span>EduCode Enterprise 2.0 · Sprint 14.2</span>
        <h1>Avaliação de intervenções e experimentação controlada</h1>
        <p>Modelos explicáveis, simulações isoladas e análises descritivas sob revisão humana.</p>
      </header>
      <section className="ai-grid">
        {modules.map(([title, description, path]) => (
          <ModuleCard key={path} title={title} description={description}>
            <NavLink className="ai-button" to={`/teacher/adaptive-insights/${path}`}>
              Abrir módulo
            </NavLink>
          </ModuleCard>
        ))}
      </section>
    </main>
  );
}
