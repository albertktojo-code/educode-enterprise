# Sprint 18.4 — Atividades integradas ao audiovisual

## Objetivo

Conectar uma publicação do EduCode Studio às atividades do EduCode Assess sem duplicar questões, respostas, tentativas ou notas.

## Incremento entregue

- O projeto de anime pode declarar `interactive_checkpoints` em `production_notes`.
- Cada checkpoint informa instante, rótulo e `assignment_id` canônico.
- A publicação valida se a atividade pertence à mesma organização e está agendada ou publicada.
- Os checkpoints válidos são ordenados e copiados para o manifesto imutável da publicação.
- O player do aluno pausa no instante configurado, apresenta a atividade e encaminha para `/aluno/atividades/:assignmentId`.
- O aluno pode continuar o vídeo; a atividade é mostrada uma vez por sessão do player.

## Responsabilidades por produto

- **EduCode Studio:** autoria audiovisual, instante do checkpoint e publicação do manifesto.
- **EduCode Practice:** experiência de prática acessada pelo aluno.
- **EduCode Assess:** atividade, questões, tentativas, respostas, correção e nota.
- **EduCode Analytics:** recebe as evidências já produzidas pelo fluxo canônico de entrega.

## Integridade e compatibilidade

- Não foi criada tabela nem armazenamento paralelo de respostas.
- Publicações antigas continuam válidas com `interactive_checkpoints` vazio.
- Checkpoints fora da duração aprovada, IDs repetidos e atividades inválidas impedem a publicação.
- Esta entrega não requer migration. A edição visual dos checkpoints no Studio fica para o próximo incremento.

## Critérios de aceite

1. Uma publicação sem checkpoints mantém o comportamento anterior.
2. Uma publicação com checkpoint válido pausa no instante definido.
3. O botão abre a atividade canônica atribuída ao aluno.
4. Uma atividade de outra organização, em rascunho ou encerrada não pode ser publicada como checkpoint.
5. Testes, lint e build são executados antes de qualquer migration.
