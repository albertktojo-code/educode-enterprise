import { useEffect, useState } from "react";
import { adaptiveEvolutionApi } from "../api";
import { ModuleCard } from "../components/ModuleCard";
import { NumberField } from "../components/NumberField";
import type { ProgressionAction, ProgressionRule } from "../types";
import "../styles.css";

export function ProgressionRulesPage() {
  const [name, setName] = useState("Avanço padrão");
  const [version, setVersion] = useState("1.0.0");
  const [mastery, setMastery] = useState(0.7);
  const [confidence, setConfidence] = useState(0.6);
  const [evidences, setEvidences] = useState(3);
  const [action, setAction] = useState<ProgressionAction>("ADVANCE");
  const [approval, setApproval] = useState(false);
  const [rules, setRules] = useState<ProgressionRule[]>([]);
  const [error, setError] = useState("");

  async function loadRules() {
    try { setRules(await adaptiveEvolutionApi.listProgressionRules()); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Falha ao listar regras."); }
  }

  useEffect(() => { void loadRules(); }, []);

  async function createRule() {
    setError("");
    try {
      await adaptiveEvolutionApi.createProgressionRule({
        name,
        version,
        description: "Regra configurada no painel da Sprint 14.1.",
        scope_type: "ORGANIZATION",
        conditions: {
          minimum_mastery_score: mastery,
          minimum_confidence: confidence,
          minimum_evidences: evidences,
          required_prerequisites: true,
          maximum_high_level_hints: 1,
        },
        result_action: action,
        priority: 100,
        requires_teacher_approval: approval,
        status: "DRAFT",
      });
      await loadRules();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Falha ao criar regra."); }
  }

  async function publish(id: string) {
    setError("");
    try { await adaptiveEvolutionApi.publishProgressionRule(id); await loadRules(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Falha ao publicar regra."); }
  }

  return (
    <main className="ae-page">
      <h1>Regras de avanço configuráveis</h1>
      <div className="ae-grid ae-grid--two">
        <ModuleCard title="Nova versão de regra" description="Regras publicadas permanecem preservadas no histórico.">
          <div className="ae-form-grid">
            <label className="ae-field"><span>Nome</span><input value={name} onChange={(event) => setName(event.target.value)} /></label>
            <label className="ae-field"><span>Versão</span><input value={version} onChange={(event) => setVersion(event.target.value)} /></label>
            <NumberField label="Domínio mínimo" value={mastery} onChange={setMastery} />
            <NumberField label="Confiança mínima" value={confidence} onChange={setConfidence} />
            <NumberField label="Evidências mínimas" value={evidences} min={0} max={100} step={1} onChange={setEvidences} />
            <label className="ae-field"><span>Ação</span><select value={action} onChange={(event) => setAction(event.target.value as ProgressionAction)}><option>ADVANCE</option><option>MAINTAIN</option><option>REVIEW</option><option>REINFORCE</option><option>RETURN_TO_PREREQUISITE</option><option>TEACHER_REVIEW</option><option>COMPLETE_PATH</option></select></label>
          </div>
          <label className="ae-check"><input type="checkbox" checked={approval} onChange={(event) => setApproval(event.target.checked)} /> Exigir aprovação docente</label>
          <button className="ae-button" type="button" onClick={createRule}>Criar regra em rascunho</button>
          {error && <p className="ae-error">{error}</p>}
        </ModuleCard>
        <ModuleCard title="Regras da organização" description="Publicação controlada por RBAC administrativo.">
          {rules.length === 0 ? <p>Nenhuma regra carregada.</p> : <div className="ae-rule-list">{rules.map((rule) => <article key={rule.id} className="ae-rule-item"><div><strong>{rule.name} · v{rule.version}</strong><p>{rule.result_action} · prioridade {rule.priority}</p><small>{rule.status}</small></div>{rule.status === "DRAFT" && <button className="ae-button ae-button--secondary" type="button" onClick={() => publish(rule.id)}>Publicar</button>}</article>)}</div>}
        </ModuleCard>
      </div>
    </main>
  );
}
