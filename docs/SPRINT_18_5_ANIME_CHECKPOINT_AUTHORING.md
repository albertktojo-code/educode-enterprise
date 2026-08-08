# Sprint 18.5 — Autoria visual de checkpoints do Anime

## Objetivo

Permitir que o professor configure visualmente as atividades interativas entregues pela Sprint 18.4, mantendo o EduCode Assess como fonte canônica para atividade, tentativa, resposta, correção e nota.

## Incremento entregue

- Nova aba **Atividades** no EduCode Studio.
- Catálogo de atividades reutilizado de `/delivery/assignments`.
- Exibição somente de atividades agendadas ou publicadas para novos vínculos.
- Criação, edição e remoção de checkpoints.
- Configuração do instante, rótulo, pausa do vídeo e obrigatoriedade pedagógica.
- Timeline com marcadores e prévia navegável da interação.
- Estado vazio com acesso ao EduCode Assess quando ainda não há atividade vinculável.
- Indicador de quantidade de interações no resumo da produção.

## Integridade e segurança

- O catálogo existente já aplica RBAC docente e isolamento por organização.
- A atualização preserva todas as demais chaves de `production_notes`.
- A publicação continua fazendo a validação definitiva do vínculo no backend.
- Nenhuma questão, tentativa, resposta ou nota é armazenada no Anime Studio.
- A entrega não cria nem exige migration.

## Compatibilidade e rollback

- Projetos sem `interactive_checkpoints` continuam sendo interpretados como uma lista vazia.
- Publicações antigas não são modificadas ao editar o rascunho dos checkpoints.
- O rollback consiste em reverter os arquivos desta sprint; não há alteração de banco para desfazer.

## Changelog

- `frontend`: autoria visual, prévia, integração com catálogo e estilos responsivos.
- `tests`: contratos estáticos da integração Studio–Assess.
- `docs`: critérios, compatibilidade e rollback desta sprint.

## Critérios de aceite

1. O professor visualiza somente atividades agendadas ou publicadas no novo formulário.
2. Um checkpoint pode ser criado, alterado e removido antes da publicação.
3. A timeline representa o instante de cada checkpoint e pode ser navegada por teclado.
4. O salvamento preserva notas de produção e manifestos já existentes.
5. O editor orienta o professor a abrir o Assess quando não existem atividades disponíveis.
6. Testes e builds são executados antes de qualquer migration.
