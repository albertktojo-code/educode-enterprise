import { useMemo, useState } from "react";
import { BatchGenerationPanel } from "./BatchGenerationPanel";
import { CharacterEditor } from "./CharacterEditor";
import { CharacterLibrary } from "./CharacterLibrary";
import { ConsistencyPanel } from "./ConsistencyPanel";
import { ScenarioLibrary } from "./ScenarioLibrary";
import type { ComicCharacter, ComicScenario, ConsistencyFinding, GenerationBatch } from "./types";
import "./styles.css";

const characters: ComicCharacter[] = [
  { id: "luna", libraryId: "hq", name: "Luna", slug: "luna", biography: "Professora curiosa que transforma problemas em aventuras.", personality: { curious: true }, identityProfile: { hair: "cacheado preto", eyes: "castanhos", glasses: true, age_group: "adulta" }, defaultWardrobe: { outfit: "uniforme azul" }, visualStyle: { style: "comic" }, promptTemplate: "Luna, professora...", negativePrompt: "sem texto", identityFingerprint: "demo", currentVersion: 4, status: "PUBLISHED" },
  { id: "leo", libraryId: "hq", name: "Léo", slug: "leo", biography: "Estudante que adora decompor desafios.", personality: { analytical: true }, identityProfile: { hair: "curto castanho", eyes: "castanhos", age_group: "adolescente" }, defaultWardrobe: { outfit: "camiseta verde" }, visualStyle: { style: "comic" }, promptTemplate: "Leo, estudante...", negativePrompt: "sem texto", identityFingerprint: "demo2", currentVersion: 2, status: "PUBLISHED" },
  { id: "nina", libraryId: "org", name: "Nina", slug: "nina", biography: "Personagem da biblioteca institucional.", personality: {}, identityProfile: { hair: "longo ruivo", eyes: "verdes", age_group: "adolescente" }, defaultWardrobe: {}, visualStyle: {}, promptTemplate: "", negativePrompt: "", identityFingerprint: "demo3", currentVersion: 1, status: "APPROVED" },
];

const scenarios: ComicScenario[] = [
  { id: "lab", libraryId: "hq", name: "Laboratório de Matemática", slug: "laboratorio-matematica", description: "Sala clara com quadro digital, mesas modulares e objetos geométricos.", locationProfile: {}, lightingProfile: {}, requiredObjects: [], identityFingerprint: "s1", currentVersion: 3, status: "PUBLISHED" },
  { id: "park", libraryId: "org", name: "Parque da Cidade", slug: "parque-cidade", description: "Área externa com árvores, pista e quiosque educacional.", locationProfile: {}, lightingProfile: {}, requiredObjects: [], identityFingerprint: "s2", currentVersion: 1, status: "APPROVED" },
];

const initialFindings: ConsistencyFinding[] = [
  { id: "f1", checkCode: "GLASSES_MISMATCH", severity: "WARNING", status: "OPEN", message: "Luna aparece sem óculos, mas o item está bloqueado na identidade principal.", pageId: "3", panelId: "4" },
  { id: "f2", checkCode: "CHARACTER_WARDROBE_CHANGED", severity: "WARNING", status: "OPEN", message: "A roupa mudou entre quadros sem transição narrativa registrada.", pageId: "4", panelId: "2" },
];

const batch: GenerationBatch = { id: "batch", name: "Gerar páginas 3 a 5", status: "RUNNING", progressPercent: 67, items: [
  { id: "i1", panelId: "quadro-07", status: "COMPLETED", retryCount: 0 },
  { id: "i2", panelId: "quadro-08", status: "COMPLETED", retryCount: 1 },
  { id: "i3", panelId: "quadro-09", status: "RUNNING", retryCount: 0 },
] };

export function ComicVisualLibrary() {
  const [selectedId, setSelectedId] = useState(characters[0].id);
  const [findings, setFindings] = useState(initialFindings);
  const selected = useMemo(() => characters.find((item) => item.id === selectedId), [selectedId]);
  return (
    <main className="cvl-shell">
      <header className="cvl-header"><div><span className="cvl-kicker">EduCode Comic Studio · Sprint 16.3</span><h1>Consistência visual e biblioteca reutilizável</h1><p>Preserve personagens, roupas, cenários e continuidade entre páginas e novas HQs.</p></div><div><button type="button">Importar elenco da HQ</button><button type="button" className="cvl-primary">Gerar quadros selecionados</button></div></header>
      <nav className="cvl-tabs" aria-label="Seções"><button type="button" className="is-active">Personagens</button><button type="button">Cenários</button><button type="button">Continuidade</button><button type="button">Biblioteca institucional</button></nav>
      <div className="cvl-layout"><CharacterLibrary characters={characters} selectedId={selectedId} onSelect={setSelectedId} onCreate={() => alert("Novo personagem")}/><CharacterEditor character={selected} onRegenerate={(intent) => alert(`Regenerar: ${intent}`)} /></div>
      <ScenarioLibrary scenarios={scenarios} />
      <ConsistencyPanel findings={findings} onResolve={(id) => setFindings((current) => current.filter((item) => item.id !== id))} />
      <BatchGenerationPanel batch={batch} />
    </main>
  );
}
