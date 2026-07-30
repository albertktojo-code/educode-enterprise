import { useState } from "react";
import { ApprovalBoard } from "./ApprovalBoard";
import { ChecklistPanel } from "./ChecklistPanel";
import { CommentSidebar } from "./CommentSidebar";
import { PublicationWizard } from "./PublicationWizard";
import { ReleaseHistory } from "./ReleaseHistory";
import type { EditorialChecklistItem, PublicationRelease, ReviewThread } from "./types";
import "./styles.css";

const sampleThreads: ReviewThread[] = [
  { id: "1", title: "Revisar habilidade BNCC", status: "OPEN", anchor_type: "PAGE", page_id: "p1" },
  { id: "2", title: "Aumentar contraste do balao", status: "RESOLVED", anchor_type: "PANEL", panel_id: "q3" },
];

const sampleChecklist: EditorialChecklistItem[] = [
  { code: "PED-01", category: "PEDAGOGICAL", label: "Objetivo pedagogico confirmado", required: true, status: "PASSED" },
  { code: "BNCC-01", category: "BNCC", label: "Habilidades BNCC revisadas", required: true, status: "PASSED" },
  { code: "A11Y-01", category: "ACCESSIBILITY", label: "Descricoes alternativas completas", required: true, status: "PENDING" },
];

const sampleReleases: PublicationRelease[] = [
  { id: "r1", release_number: 1, release_name: "Primeira publicacao", release_hash: "e2c1f1147ac45c98", status: "PUBLISHED" },
];

export function ReviewWorkspace() {
  const [selected, setSelected] = useState<ReviewThread | undefined>(sampleThreads[0]);
  const blockers = sampleChecklist
    .filter((item) => item.required && item.status !== "PASSED" && item.status !== "WAIVED")
    .map((item) => item.label);

  return (
    <main className="crp-layout">
      <CommentSidebar threads={sampleThreads} selectedId={selected?.id} onSelect={setSelected} />
      <section className="crp-main">
        <header className="crp-hero">
          <div>
            <span className="crp-eyebrow">Sprint 16.4</span>
            <h1>Revisao editorial da HQ</h1>
            <p>Comente por pagina, quadro ou camada, acompanhe aprovacoes e publique releases rastreaveis.</p>
          </div>
          <button type="button">Abrir pre-visualizacao</button>
        </header>
        <div className="crp-canvas-placeholder">
          <div>
            <strong>{selected?.title ?? "Selecione um comentario"}</strong>
            <p>O comentario selecionado sera destacado diretamente na pagina da HQ.</p>
          </div>
        </div>
        <div className="crp-grid">
          <ChecklistPanel items={sampleChecklist} />
          <ApprovalBoard
            minimumApprovals={2}
            approvals={[
              { reviewer: "Coordenacao pedagogica", role: "PEDAGOGICAL_REVIEWER", decision: "APPROVE" },
              { reviewer: "Revisao de acessibilidade", role: "ACCESSIBILITY_REVIEWER", decision: "PENDING" },
            ]}
          />
          <PublicationWizard ready={blockers.length === 0} blockers={blockers} />
          <ReleaseHistory releases={sampleReleases} />
        </div>
      </section>
    </main>
  );
}
