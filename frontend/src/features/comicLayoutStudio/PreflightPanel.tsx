import type { PreflightFinding } from "./types";

interface Props { findings: PreflightFinding[]; onRun: () => void; }

export function PreflightPanel({ findings, onRun }: Props) {
  const errors = findings.filter((item) => item.severity === "ERROR").length;
  const warnings = findings.filter((item) => item.severity === "WARNING").length;
  return (
    <section className="cls-preflight">
      <header><div><span className="cls-eyebrow">Pré-impressão</span><h2>Verificação da página</h2></div><button type="button" onClick={onRun}>Verificar agora</button></header>
      <div className="cls-preflight-summary"><span>{errors} erros</span><span>{warnings} avisos</span><span>{findings.length - errors - warnings} informações</span></div>
      {findings.length === 0 ? <p>Nenhuma verificação executada nesta edição.</p> : <ul>{findings.map((item, index) => <li key={`${item.code}-${index}`} className={`severity-${item.severity.toLowerCase()}`}><strong>{item.code}</strong><span>{item.message}</span></li>)}</ul>}
    </section>
  );
}
