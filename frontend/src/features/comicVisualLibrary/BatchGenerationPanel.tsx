import type { GenerationBatch } from "./types";

export function BatchGenerationPanel({ batch }: { batch: GenerationBatch }) {
  return (
    <section className="cvl-card">
      <header className="cvl-section-header"><div><span className="cvl-kicker">Produção em lote</span><h2>{batch.name}</h2></div><span className="cvl-status">{batch.status}</span></header>
      <div className="cvl-progress" aria-label={`${batch.progressPercent}% concluído`}><div style={{ width: `${batch.progressPercent}%` }} /></div>
      <p>{batch.progressPercent}% · resultados concluídos são preservados em caso de falha parcial.</p>
      <div className="cvl-batch-items">{batch.items.map((item) => <div key={item.id}><span>Quadro {item.panelId.slice(0, 6)}</span><strong>{item.status}</strong><small>Tentativas: {item.retryCount}</small></div>)}</div>
      <div className="cvl-inline-actions"><button type="button">Pausar</button><button type="button">Repetir falhas</button><button type="button">Continuar em segundo plano</button></div>
    </section>
  );
}
