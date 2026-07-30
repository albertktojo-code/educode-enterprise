import type {
  ContinuityIssue,
  ContinuityRow,
} from "./types";

interface Props {
  open: boolean;
  rows: ContinuityRow[];
  issues: ContinuityIssue[];
  onClose: () => void;
  onEdit: (row: ContinuityRow) => void;
}

const fieldLabels: Record<string, string> = {
  character: "Personagem",
  outfit: "Roupa",
  scenario: "Cenário",
  important_object: "Objeto",
  time_of_day: "Horário",
  emotion: "Emoção",
  palette: "Paleta",
};

export function ContinuityPanel({
  open,
  rows,
  issues,
  onClose,
  onEdit,
}: Props) {
  if (!open) return null;

  return (
    <div className="continuity-overlay" role="dialog" aria-modal="true">
      <section className="continuity-dialog">
        <header>
          <div>
            <span className="hq-eyebrow">Continuidade visual</span>
            <h2>Mapa da HQ</h2>
          </div>
          <button type="button" onClick={onClose} aria-label="Fechar">
            ×
          </button>
        </header>

        <div className="continuity-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Página</th>
                <th>Personagem</th>
                <th>Roupa</th>
                <th>Cenário</th>
                <th>Objeto</th>
                <th>Horário</th>
                <th>Emoção</th>
                <th>Paleta</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.pageId}>
                  <td>
                    {row.pageType === "COVER"
                      ? "Capa"
                      : row.pageNumber}
                  </td>
                  <td>{row.character || "—"}</td>
                  <td>{row.outfit || "—"}</td>
                  <td>{row.scenario || "—"}</td>
                  <td>{row.important_object || "—"}</td>
                  <td>{row.time_of_day || "—"}</td>
                  <td>{row.emotion || "—"}</td>
                  <td>{row.palette || "—"}</td>
                  <td>
                    <button type="button" onClick={() => onEdit(row)}>
                      Editar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="continuity-issues">
          <h3>Alertas de continuidade</h3>
          {!issues.length ? (
            <p>Nenhuma inconsistência detectada com os dados preenchidos.</p>
          ) : (
            issues.map((issue, index) => (
              <article key={`${issue.field}-${index}`}>
                <strong>
                  {fieldLabels[issue.field] ?? issue.field}
                </strong>
                <span>{issue.message}</span>
                <small>
                  {issue.from_value} → {issue.to_value}
                </small>
              </article>
            ))
          )}
        </div>
        <footer>
          <small>
            Os alertas são sugestões. Nenhuma alteração é aplicada
            automaticamente.
          </small>
          <button type="button" onClick={onClose}>
            Fechar mapa
          </button>
        </footer>
      </section>
    </div>
  );
}
