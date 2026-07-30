import { useMemo } from "react";
import type { GenerationStep } from "./types";
import "./styles.css";

const defaultSteps: GenerationStep[] = [
  { stepCode: "PEDAGOGICAL_PLAN", title: "Objetivos pedagogicos", playfulMessage: "Ajustando os superpoderes pedagogicos...", status: "COMPLETED", progressWeight: 1 },
  { stepCode: "BNCC_VALIDATION", title: "Habilidades BNCC", playfulMessage: "Conferindo se a BNCC participa da aventura...", status: "COMPLETED", progressWeight: 1 },
  { stepCode: "PAGE_LAYOUT", title: "Paginas e grids", playfulMessage: "Organizando os quadros para ninguem sair da pagina...", status: "RUNNING", progressWeight: 1 },
  { stepCode: "IMAGE_GENERATION", title: "Ilustracoes", playfulMessage: "Os personagens estao ensaiando suas falas...", status: "PENDING", progressWeight: 3 },
  { stepCode: "ACCESSIBILITY", title: "Acessibilidade", playfulMessage: "Preparando uma leitura confortavel para todos...", status: "PENDING", progressWeight: 1 },
];

export function GenerationLoadingPage({ steps = defaultSteps }: { steps?: GenerationStep[] }) {
  const progress = useMemo(() => {
    const total = steps.reduce((sum, step) => sum + step.progressWeight, 0);
    const complete = steps.reduce((sum, step) => sum + (step.status === "COMPLETED" ? step.progressWeight : step.status === "RUNNING" ? step.progressWeight / 2 : 0), 0);
    return Math.round((complete / total) * 100);
  }, [steps]);
  const current = steps.find((step) => step.status === "RUNNING") ?? steps.at(-1);

  return (
    <main className="hq-generation-page" aria-live="polite">
      <section className="hq-generation-card">
        <div className="hq-generation-illustration" aria-hidden="true"><span>✦</span><span>▧</span><span>✎</span></div>
        <span className="hq-eyebrow">Sua HQ esta ganhando vida</span>
        <h1>{current?.playfulMessage}</h1>
        <p>Voce pode voltar ao painel. O trabalho continuara em segundo plano e nenhuma pagina sera perdida.</p>
        <div className="hq-progress" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${progress}%` }} /></div>
        <strong>{progress}% concluido</strong>
        <ol className="hq-generation-steps">
          {steps.map((step) => <li key={step.stepCode} className={`is-${step.status.toLowerCase()}`}><span /> <div><strong>{step.title}</strong><small>{step.status === "RUNNING" ? step.playfulMessage : step.status}</small></div></li>)}
        </ol>
        <div className="hq-toolbar-actions"><button type="button">Continuar em segundo plano</button><button type="button">Ver detalhes</button><button type="button" className="hq-danger">Cancelar com seguranca</button></div>
      </section>
    </main>
  );
}
