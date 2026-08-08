# Sprint 18.6 — Continuidade entre vídeo e atividade

## Objetivo

Manter o aluno no fluxo pedagógico iniciado por um checkpoint audiovisual, usando o progresso canônico do EduCode Assess para retornar, retomar e liberar o vídeo.

## Incremento entregue

- O player consulta `/student/assignments` e associa cada checkpoint à situação real da atividade do aluno.
- A interação apresenta os estados pendente, em andamento, concluída e indisponível.
- O vínculo para a atividade inclui um retorno interno ao projeto e ao checkpoint de origem.
- Depois da entrega, a página da atividade retorna automaticamente ao vídeo.
- O vídeo é reposicionado exatamente no instante do checkpoint informado no retorno.
- O progresso das atividades é atualizado na abertura e quando a janela recupera foco.
- Checkpoints obrigatórios bloqueiam a continuação enquanto uma atividade atribuída permanece pendente.
- Uma atividade indisponível para o aluno não o prende em um bloqueio impossível; o problema é informado e o vídeo é liberado.

## Segurança e domínios canônicos

- O endereço de retorno aceita somente o caminho interno `/anime-library`.
- URLs externas, caminhos relativos inseguros e outros destinos são ignorados.
- Tentativas, respostas, entrega, correção e conclusão continuam no Assessment Delivery.
- O player somente consulta e apresenta o estado canônico; não cria um segundo progresso avaliativo.

## Compatibilidade e rollback

- Checkpoints opcionais preservam o comportamento anterior de continuação imediata.
- Vídeos sem checkpoints continuam funcionando sem consultas específicas por atividade.
- A posição local continua sendo usada quando não há retorno explícito de checkpoint.
- O rollback consiste em reverter os arquivos desta sprint; não há alteração de banco.

## Changelog

- `frontend/animeStudio`: retorno contextual, retomada exata, estados e bloqueio pedagógico.
- `frontend/StudentAssignmentPage`: retorno interno validado após entrega.
- `tests`: contratos de segurança, continuidade e reutilização do Assessment Delivery.

## Critérios de aceite

1. O aluno abre uma atividade a partir de um checkpoint e retorna ao mesmo vídeo.
2. O vídeo volta ao instante exato do checkpoint.
3. A conclusão exibida vem de `/student/assignments`.
4. Um checkpoint obrigatório com atividade pendente não permite continuar o vídeo.
5. Uma atividade concluída libera imediatamente o checkpoint.
6. Um vínculo indisponível não cria bloqueio permanente.
7. Nenhuma URL externa pode ser usada como retorno.
8. Testes e builds são executados antes de qualquer migration.
