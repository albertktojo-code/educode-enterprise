# Sprint 17.4.3 — Legendas sincronizadas

## Incremento entregue

- Edição de texto, locutor, tipo, cena e janela temporal de cada legenda.
- Preview sincronizado por posição, com legenda ativa sobre a mídia disponível.
- Detecção visual e bloqueio no backend de intervalos sobrepostos no mesmo idioma.
- Importação de arquivos SRT e WebVTT com validação prévia.
- Exportação das legendas ordenadas para SRT e WebVTT.
- Suporte aos tipos diálogo, narração, som importante e audiodescrição.

## Reuso e governança

A implementação reutiliza `AnimeCaptionCue`, o endpoint `PATCH`, o projeto audiovisual canônico, auditoria e isolamento por organização. Não há nova tabela, coluna ou migration. Toda alteração devolve o projeto ao estado de rascunho e incrementa sua revisão.

## Validação e rollback

Os contratos cobrem edição, acessibilidade, isolamento e detecção de sobreposição. O parser/serializador é validado com arquivos SRT e VTT. O rollback remove os controles e a validação de sobreposição sem alterar dados ou schema.
