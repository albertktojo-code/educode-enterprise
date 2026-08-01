interface Approval {
  reviewer: string;
  role: string;
  decision: "APPROVE" | "REQUEST_CHANGES" | "REJECT" | "PENDING";
}

interface Props {
  approvals: Approval[];
  minimumApprovals: number;
}

export function ApprovalBoard({ approvals, minimumApprovals }: Props) {
  const approved = approvals.filter((item) => item.decision === "APPROVE").length;
  return (
    <section className="crp-card">
      <header className="crp-card-header">
        <div>
          <h2>Aprovacoes</h2>
          <p>{approved} de {minimumApprovals} aprovacoes minimas</p>
        </div>
      </header>
      <div className="crp-approval-grid">
        {approvals.map((item) => (
          <article key={`${item.reviewer}-${item.role}`}>
            <strong>{item.reviewer}</strong>
            <small>{item.role}</small>
            <span className={`crp-decision ${item.decision.toLowerCase()}`}>{item.decision}</span>
          </article>
        ))}
      </div>
    </section>
  );
}
