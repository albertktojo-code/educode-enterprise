import { Link } from "react-router-dom";

export function ComicStudioEntryPage() {
  return (
    <main className="hq-entry-page">
      <span className="hq-eyebrow">Criar material e Minhas HQs</span>
      <h1>Planeje páginas, grids e narrativa antes de gerar as imagens</h1>
      <p>Escolha grids diferentes página por página, escreva o roteiro completo ou gere um rascunho com IA, preserve a continuidade visual e distribua a história conforme a extensão real da HQ.</p>
      <div className="hq-entry-actions">
        <Link to="/teacher/comic-studio/editor/demo" className="hq-primary">Abrir editor de paginas</Link>
        <Link to="/teacher/comic-studio/generation/demo">Ver experiencia de carregamento</Link>
      </div>
    </main>
  );
}
