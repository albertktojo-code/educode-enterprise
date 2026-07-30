# Sprint 09.1 — Storyboard e pré-visualização

Esta sprint adiciona uma camada de revisão separada do canvas e deriva o storyboard diretamente da estrutura da HQ.

## Entregas

- Storyboard automático por página e quadro.
- Linha emocional, ritmo, pistas, falsas soluções, reviravoltas e resolução.
- Tela de pré-visualização exclusiva do professor.
- Modos estudante, professor, impressão, página única, dupla, rolagem e celular.
- Miniaturas multipágina com estado de revisão.
- Aprovação ou solicitação de correção por página e quadro.
- Bloqueio de páginas aprovadas.
- Comentários vinculados à página ou quadro, com ponto visual opcional.
- Comparação entre versões da HQ.
- Simulação sanitizada da visão do estudante.
- Checklist de prontidão para publicação.
- Acesso direto do storyboard e da prévia para o canvas.

## Endereços

- `/hqs/{comic_id}/preview`
- `/storyboards/{comic_id}`

## Migration

`0015_storyboard_preview`

## Segurança

Storyboard, validação, comparação e simulação de prévia são acessíveis apenas a proprietário, administrador ou professor da organização. Estudantes continuam usando exclusivamente a área de atividades publicadas.
