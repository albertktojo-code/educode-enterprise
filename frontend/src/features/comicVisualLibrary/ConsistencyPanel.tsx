import type { ConsistencyFinding } from "./types";

interface Props {
  findings: ConsistencyFinding[];
  onResolve: (id: string) => void;
}

export function ConsistencyPanel({ findings, onResolve }: Props) {
  return (
    <section className="cvl-card">
      <header className="cvl-section-header"><div><span className="cvl-kicker">Verificação antes de gerar</span><h2>Consistência visual e narrativa</h2></div><button type="button">Verificar HQ inteira</button></header>
      {findings.length === 0 ? <div className="cvl-empty">✓ Nenhuma inconsistência aberta.</div> : <div className="cvl-findings">
        {findings.map((finding) => <article key={finding.id} className={`severity-${finding.severity.toLowerCase()}`}><span>{finding.severity}</span><div><strong>{finding.checkCode.replaceAll('_', ' ')}</strong><p>{finding.message}</p><small>Página {finding.pageId ?? '—'} · quadro {finding.panelId ?? '—'}</small></div><div><button type="button" onClick={() => onResolve(finding.id)}>Corrigir</button><button type="button">Aceitar exceção</button></div></article>)}
      </div>}
    </section>
  );
}
