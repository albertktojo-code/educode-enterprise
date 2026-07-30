interface Props {
  open: boolean;
  originalReference?: string | null;
  candidateReference?: string | null;
  title: string;
  onKeepOriginal: () => void;
  onApplyCandidate: () => void;
  onGenerateAgain: () => void;
}

export function ComparisonDialog({
  open,
  originalReference,
  candidateReference,
  title,
  onKeepOriginal,
  onApplyCandidate,
  onGenerateAgain,
}: Props) {
  if (!open) return null;

  return (
    <div className="comparison-overlay" role="dialog" aria-modal="true">
      <section className="comparison-dialog">
        <header>
          <span className="hq-eyebrow">Comparação obrigatória</span>
          <h2>{title}</h2>
          <p>Nada será substituído sem confirmação do professor.</p>
        </header>
        <div className="comparison-grid">
          <article>
            <strong>Versão atual</strong>
            <div
              className="comparison-preview"
              style={
                originalReference
                  ? {
                      backgroundImage: `url("${originalReference}")`,
                    }
                  : undefined
              }
            >
              {!originalReference ? "Sem imagem atual" : null}
            </div>
          </article>
          <article>
            <strong>Nova variação</strong>
            <div
              className="comparison-preview candidate"
              style={
                candidateReference
                  ? {
                      backgroundImage: `url("${candidateReference}")`,
                    }
                  : undefined
              }
            >
              {!candidateReference
                ? "Resultado aguardando carregamento"
                : null}
            </div>
          </article>
        </div>
        <footer>
          <button type="button" onClick={onKeepOriginal}>
            Manter original
          </button>
          <button type="button" onClick={onGenerateAgain}>
            Gerar outra variação
          </button>
          <button
            type="button"
            className="hq-primary"
            disabled={!candidateReference}
            onClick={onApplyCandidate}
          >
            Aplicar nova imagem
          </button>
        </footer>
      </section>
    </div>
  );
}
