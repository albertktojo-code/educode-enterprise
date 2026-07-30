import { useMemo, useState } from "react";

interface Props {
  ready: boolean;
  blockers: string[];
  onPublish?: (target: string) => void;
}

export function PublicationWizard({ ready, blockers, onPublish }: Props) {
  const [target, setTarget] = useState("CLASSROOM");
  const message = useMemo(
    () => ready ? "Todos os requisitos foram atendidos." : `${blockers.length} pendencias impedem a publicacao.`,
    [ready, blockers.length],
  );

  return (
    <section className="crp-card">
      <h2>Publicar HQ</h2>
      <p>{message}</p>
      {!ready && (
        <ul className="crp-blockers">
          {blockers.map((item) => <li key={item}>{item}</li>)}
        </ul>
      )}
      <label>
        Destino
        <select value={target} onChange={(event) => setTarget(event.target.value)}>
          <option value="CLASSROOM">Turma</option>
          <option value="GROUP">Grupo</option>
          <option value="STUDENT">Estudante</option>
          <option value="INSTITUTIONAL_LIBRARY">Biblioteca institucional</option>
        </select>
      </label>
      <button type="button" disabled={!ready} onClick={() => onPublish?.(target)}>
        Criar release e publicar
      </button>
    </section>
  );
}
