import type { ComicCharacter } from "./types";

interface Props {
  characters: ComicCharacter[];
  selectedId?: string;
  onSelect: (id: string) => void;
  onCreate: () => void;
}

export function CharacterLibrary({ characters, selectedId, onSelect, onCreate }: Props) {
  return (
    <section className="cvl-card cvl-library-panel">
      <header className="cvl-section-header">
        <div><span className="cvl-kicker">Elenco reutilizável</span><h2>Personagens</h2></div>
        <button type="button" onClick={onCreate}>+ Novo personagem</button>
      </header>
      <div className="cvl-search-row"><input aria-label="Buscar personagens" placeholder="Buscar por nome, roupa ou HQ" /><select aria-label="Filtrar biblioteca"><option>Todas as bibliotecas</option><option>Minha biblioteca</option><option>Biblioteca institucional</option></select></div>
      <div className="cvl-character-grid">
        {characters.map((character) => (
          <button key={character.id} type="button" className={`cvl-character-tile ${selectedId === character.id ? "is-selected" : ""}`} onClick={() => onSelect(character.id)}>
            <div className="cvl-avatar" aria-hidden="true">{character.name.slice(0, 1)}</div>
            <strong>{character.name}</strong>
            <span>v{character.currentVersion} · {character.status}</span>
            <small>{String(character.identityProfile.hair ?? "visual definido")}</small>
          </button>
        ))}
      </div>
    </section>
  );
}
