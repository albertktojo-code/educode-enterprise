# Sprint 17.4.4 — Renderização e versões

## Incremento entregue

- Progresso detalhado do job de render, etapa atual e tentativas.
- Reprocessamento de renders com falha pelo fluxo canônico de operações.
- Seleção de qualquer versão no histórico imutável.
- Comparação lado a lado de dois previews renderizados.
- Restauração de uma versão anterior aprovada como versão ativa.
- Aprovação de um render passa a registrá-lo como versão ativa do projeto.

## Reuso e governança

A sprint reutiliza `AnimeRender.source_snapshot`, `BackgroundJob`, tentativas, eventos, retry, ativos institucionais, revisão humana e auditoria. A restauração não altera nem recria cenas: apenas seleciona um render aprovado e imutável como versão ativa para publicação posterior.

Não há nova tabela, coluna ou migration. O identificador da versão ativa é armazenado em `AnimeProject.production_notes`, campo JSON canônico já existente.

## Segurança e rollback

A restauração exige perfil revisor, restringe projeto e render pela organização e aceita somente versões aprovadas com arquivo concluído. O rollback remove o endpoint e os controles de seleção sem apagar renders, jobs ou ativos.
