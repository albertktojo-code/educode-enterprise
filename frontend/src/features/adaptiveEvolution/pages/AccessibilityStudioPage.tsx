import { useState } from "react";
import { adaptiveEvolutionApi } from "../api";
import { ModuleCard } from "../components/ModuleCard";
import type { AccessibleVersionPreview, AdaptationType } from "../types";
import "../styles.css";

export function AccessibilityStudioPage() {
  const [title, setTitle] = useState("Atividade sobre frações");
  const [content, setContent] = useState("Identifique as informações e posteriormente efetue o cálculo solicitado; por fim, justifique sua resposta.");
  const [adaptation, setAdaptation] = useState<AdaptationType>("PLAIN_LANGUAGE");
  const [preview, setPreview] = useState<AccessibleVersionPreview | null>(null);
  const [error, setError] = useState("");

  async function generatePreview() {
    setError("");
    try {
      setPreview(await adaptiveEvolutionApi.previewAccessibleVersion({
        source_resource_type: "ACTIVITY",
        source_resource_id: crypto.randomUUID(),
        title,
        content,
        adaptation_type: adaptation,
        learning_objective: "Resolver e justificar problemas com frações.",
        expected_answer: "Resposta definida na atividade original.",
        assessment_criteria: ["Representação correta", "Justificativa"],
        source_images_without_description: 0,
      }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha ao gerar versão acessível.");
    }
  }

  return (
    <main className="ae-page">
      <h1>Estúdio de versões acessíveis</h1>
      <div className="ae-grid ae-grid--two">
        <ModuleCard title="Material original" description="A versão original será preservada.">
          <label className="ae-field"><span>Título</span><input value={title} onChange={(event) => setTitle(event.target.value)} /></label>
          <label className="ae-field"><span>Conteúdo</span><textarea rows={10} value={content} onChange={(event) => setContent(event.target.value)} /></label>
          <label className="ae-field"><span>Adaptação</span><select value={adaptation} onChange={(event) => setAdaptation(event.target.value as AdaptationType)}><option value="PLAIN_LANGUAGE">Linguagem simples</option><option value="STEP_BY_STEP">Passo a passo</option><option value="SCREEN_READER">Leitor de tela</option><option value="LARGE_PRINT">Fonte ampliada</option><option value="HIGH_CONTRAST">Alto contraste</option><option value="REDUCED_VISUAL_STIMULUS">Redução de estímulos</option></select></label>
          <button className="ae-button" type="button" onClick={generatePreview}>Criar prévia</button>
          {error && <p className="ae-error">{error}</p>}
        </ModuleCard>
        <ModuleCard title="Versão gerada" description="Publicação bloqueada até revisão quando houver alteração pedagógica.">
          {preview ? <><h3>{preview.title}</h3><pre className="ae-preview">{preview.content}</pre><p>Equivalência: <strong>{preview.equivalence_status}</strong></p>{preview.warnings.map((warning) => <p className="ae-warning" key={warning}>{warning}</p>)}</> : <p>Gere uma prévia para comparar com o original.</p>}
        </ModuleCard>
      </div>
    </main>
  );
}
