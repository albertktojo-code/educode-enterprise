import type { ReactNode } from "react";

interface Props {
  title: string;
  description: string;
  children?: ReactNode;
}

export function ModuleCard({ title, description, children }: Props) {
  return (
    <article className="ai-card">
      <h2>{title}</h2>
      <p>{description}</p>
      {children}
    </article>
  );
}
