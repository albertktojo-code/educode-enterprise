import { Link } from "react-router-dom";

const groups = [
  {
    title: "HQ e producao visual",
    description: "Editor de paginas, diagramacao, biblioteca visual e fluxo editorial.",
    links: [
      ["Criar HQ no novo editor", "/teacher/comic-studio"],
      ["Biblioteca visual", "/admin/comic-visual-library"],
      ["Publicacoes editoriais", "/admin/comic-publications"],
      ["Leitor e apresentações", "/comic-reader"],
      ["Analytics de leitura", "/teacher/comic-reader-analytics"],
      ["Intervenções com HQs", "/teacher/interventions"],
      ["Eficácia das intervenções", "/teacher/intervention-effectiveness"],
      ["Governança institucional", "/admin/institutional-governance"],
    ],
  },
  {
    title: "Avaliacoes integradas",
    description: "Banco de questoes, entrega, revisao, instrumentos externos e analytics.",
    links: [
      ["Assessment Hub", "/teacher/assessment-hub"],
      ["Aplicacao de avaliacoes", "/teacher/assessment-delivery"],
      ["Revisao e rubricas", "/teacher/assessment-review"],
      ["Analytics de avaliacoes", "/teacher/assessment-analytics"],
      ["Governanca de instrumentos", "/admin/instrument-governance"],
    ],
  },
  {
    title: "Aprendizagem adaptativa",
    description: "Pistas, acessibilidade, modelos, simulacoes e historico de intervencoes.",
    links: [
      ["Evolucao adaptativa", "/teacher/adaptive-evolution"],
      ["Insights adaptativos", "/teacher/adaptive-insights"],
    ],
  },
];

export function AdvancedResourcesPage() {
  return (
    <section>
      <header className="page-header">
        <div>
          <span className="eyebrow">SPRINT 16.9</span>
          <h1>Recursos avancados consolidados</h1>
          <p>
            Acesso central aos modulos incrementais, agora integrados a autenticacao,
            navegacao e infraestrutura oficial do EduCode.
          </p>
        </div>
      </header>

      <div className="dashboard-grid">
        {groups.map((group) => (
          <article className="panel" key={group.title}>
            <h2>{group.title}</h2>
            <p>{group.description}</p>
            <div className="button-row">
              {group.links.map(([label, path]) => (
                <Link key={path} to={path}>
                  {label}
                </Link>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
