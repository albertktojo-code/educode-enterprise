import { useState } from "react";
import { adaptiveEvolutionApi } from "../api";
import { ModuleCard } from "../components/ModuleCard";
import type { GraduatedHint, HintLevel } from "../types";
import "../styles.css";

const levels: Array<{ value: HintLevel; label: string; order: number }> = [
  { value: "ORIENTATION", label: "1 — Orientação geral", order: 1 },
  { value: "STRATEGY", label: "2 — Estratégia", order: 2 },
  { value: "SPECIFIC", label: "3 — Pista específica", order: 3 },
  { value: "SIMILAR_EXAMPLE", label: "4 — Exemplo semelhante", order: 4 },
  { value: "GUIDED_SOLUTION", label: "5 — Resolução orientada", order: 5 },
];

export function HintStudioPage() {
  const [resourceType, setResourceType] = useState("QUESTION");
  const [resourceId, setResourceId] = useState<string>(crypto.randomUUID());
  const [level, setLevel] = useState<HintLevel>("ORIENTATION");
  const [title, setTitle] = useState("Comece pelos dados do problema");
  const [content, setContent] = useState("Identifique primeiro quais informações foram fornecidas.");
  const [hints, setHints] = useState<GraduatedHint[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const selectedLevel = levels.find((item) => item.value === level) ?? levels[0];

  async function loadHints() {
    setError("");
    try {
      setHints(await adaptiveEvolutionApi.listHints(resourceType, resourceId));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha ao listar pistas.");
    }
  }

  async function createHint() {
    setError("");
    setMessage("");
    try {
      await adaptiveEvolutionApi.createHint({
        resource_type: resourceType,
        resource_id: resourceId,
        level,
        level_order: selectedLevel.order,
        title,
        content,
        release_rule: { manual: true, after_incorrect_attempts: selectedLevel.order },
        penalty_rule: { affects_score: false },
        version: 1,
        status: "PUBLISHED",
      });
      setMessage("Pista cadastrada e vinculada ao recurso.");
      await loadHints();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha ao criar pista.");
    }
  }

  return (
    <main className="ae-page">
      <h1>Estúdio de pistas graduais</h1>
      <div className="ae-grid ae-grid--two">
        <ModuleCard title="Nova pista" description="A resposta final não é exibida automaticamente.">
          <div className="ae-form-grid">
            <label className="ae-field"><span>Tipo de recurso</span><select value={resourceType} onChange={(event) => setResourceType(event.target.value)}><option>QUESTION</option><option>ACTIVITY</option><option>QUIZ</option><option>COMIC</option></select></label>
            <label className="ae-field"><span>ID do recurso</span><input value={resourceId} onChange={(event) => setResourceId(event.target.value)} /></label>
            <label className="ae-field"><span>Nível</span><select value={level} onChange={(event) => setLevel(event.target.value as HintLevel)}>{levels.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
            <label className="ae-field"><span>Título</span><input value={title} onChange={(event) => setTitle(event.target.value)} /></label>
          </div>
          <label className="ae-field"><span>Conteúdo da pista</span><textarea rows={5} value={content} onChange={(event) => setContent(event.target.value)} /></label>
          <div className="ae-actions"><button className="ae-button" type="button" onClick={createHint}>Salvar pista</button><button className="ae-button ae-button--secondary" type="button" onClick={loadHints}>Atualizar lista</button></div>
          {message && <p className="ae-success">{message}</p>}{error && <p className="ae-error">{error}</p>}
        </ModuleCard>
        <ModuleCard title="Pistas do recurso" description={`${hints.length} pista(s) cadastrada(s).`}>
          {hints.length === 0 ? <p>Nenhuma pista carregada.</p> : <ol className="ae-hint-list">{hints.map((hint) => <li key={hint.id}><strong>{hint.level_order}. {hint.title}</strong><p>{hint.content}</p><small>{hint.level} · versão {hint.version} · {hint.status}</small></li>)}</ol>}
        </ModuleCard>
      </div>
    </main>
  );
}
