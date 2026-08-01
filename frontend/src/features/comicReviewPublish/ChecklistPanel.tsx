import type { EditorialChecklistItem } from "./types";

interface Props {
  items: EditorialChecklistItem[];
}

export function ChecklistPanel({ items }: Props) {
  const completed = items.filter((item) => item.status === "PASSED" || item.status === "WAIVED").length;
  const blocked = items.some((item) => item.required && item.status !== "PASSED" && item.status !== "WAIVED");

  return (
    <section className="crp-card">
      <header className="crp-card-header">
        <div>
          <h2>Checklist editorial</h2>
          <p>{completed} de {items.length} itens revisados</p>
        </div>
        <span className={blocked ? "crp-badge warning" : "crp-badge success"}>
          {blocked ? "Publicacao bloqueada" : "Pronto"}
        </span>
      </header>
      <ul className="crp-checklist">
        {items.map((item) => (
          <li key={item.code}>
            <span aria-hidden="true">{item.status === "PASSED" ? "✓" : item.status === "FAILED" ? "!" : "○"}</span>
            <div>
              <strong>{item.label}</strong>
              <small>{item.category}{item.required ? " · obrigatorio" : ""}</small>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
