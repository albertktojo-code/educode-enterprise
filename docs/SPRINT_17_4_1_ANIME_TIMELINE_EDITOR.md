# Sprint 17.4.1 — Timeline editavel

## Entrega

- Reordenacao atomica de todas as cenas, com auditoria e isolamento por organizacao.
- Arrastar e soltar na timeline, com botoes equivalentes para uso por teclado.
- Edicao de titulo, duracao, enquadramento, movimento de camera e transicao.
- Divisao de uma cena em duas partes renderizaveis com pelo menos 500 ms.
- Preservacao da midia, origem da HQ, continuidade e metadados pedagogicos ao dividir.
- Incremento da revisao do projeto e retorno ao estado de rascunho apos alteracoes.

## Banco de dados e rollback

A sprint reutiliza `anime_scenes`, revisoes e auditoria existentes. Nao ha migration.
O rollback remove as rotas e controles de timeline sem alterar ou excluir o schema instalado.
