import type { ComicCharacter } from "./types";

interface Props {
  character?: ComicCharacter;
  onRegenerate: (intent: string) => void;
}

const lockLabels = ["Rosto", "Cabelo", "Roupa", "Acessórios", "Estilo", "Enquadramento"];

export function CharacterEditor({ character, onRegenerate }: Props) {
  if (!character) return <aside className="cvl-card cvl-inspector"><p>Selecione um personagem para editar identidade, roupas e versões.</p></aside>;
  return (
    <aside className="cvl-card cvl-inspector">
      <span className="cvl-kicker">Identidade visual</span>
      <h2>{character.name}</h2>
      <p>{character.biography || "Personagem persistente vinculado à biblioteca da HQ."}</p>
      <div className="cvl-version-line"><span>Versão atual</span><strong>v{character.currentVersion}</strong><button type="button">Comparar versões</button></div>
      <h3>Elementos bloqueados</h3>
      <div className="cvl-lock-grid">{lockLabels.map((label, index) => <label key={label}><input type="checkbox" defaultChecked={index < 4} /> 🔒 {label}</label>)}</div>
      <h3>Variação ativa</h3>
      <select aria-label="Variação ativa"><option>Uniforme escolar</option><option>Jaleco de laboratório</option><option>Roupa casual</option></select>
      <h3>Regeneração orientada</h3>
      <div className="cvl-action-grid">
        {['Expressão facial', 'Pose', 'Roupa', 'Iluminação'].map((item) => <button key={item} type="button" onClick={() => onRegenerate(item)}>{item}</button>)}
      </div>
      <button type="button" className="cvl-primary">Salvar nova versão</button>
    </aside>
  );
}
