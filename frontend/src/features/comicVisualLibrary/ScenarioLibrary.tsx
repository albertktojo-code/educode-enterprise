import type { ComicScenario } from "./types";

export function ScenarioLibrary({ scenarios }: { scenarios: ComicScenario[] }) {
  return (
    <section className="cvl-card">
      <header className="cvl-section-header"><div><span className="cvl-kicker">Continuidade de ambiente</span><h2>Cenários persistentes</h2></div><button type="button">+ Novo cenário</button></header>
      <div className="cvl-scenario-list">
        {scenarios.map((scenario) => (
          <article key={scenario.id}><div className="cvl-scenario-preview" aria-hidden="true">▦</div><div><strong>{scenario.name}</strong><p>{scenario.description}</p><span>v{scenario.currentVersion} · {scenario.status}</span></div><button type="button">Usar na HQ</button></article>
        ))}
      </div>
    </section>
  );
}
