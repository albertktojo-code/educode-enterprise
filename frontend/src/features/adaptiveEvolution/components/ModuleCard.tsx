import type { ReactNode } from "react";

interface ModuleCardProps {
  title: string;
  description: string;
  status?: string;
  children?: ReactNode;
}

export function ModuleCard({ title, description, status = "Disponível", children }: ModuleCardProps) {
  return (
    <section className="ae-card">
      <header className="ae-card__header">
        <div>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
        <span className="ae-badge">{status}</span>
      </header>
      {children}
    </section>
  );
}
