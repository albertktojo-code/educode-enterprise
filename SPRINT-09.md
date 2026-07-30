# Sprint 09 — Publicação, Área do Estudante e Entrega de Atividades

## Objetivo

Transformar os pacotes pedagógicos da Sprint 08 em publicações imutáveis, distribuí-las para turmas ou usuários específicos e registrar leitura, tentativas, respostas, correções e resultados de aprendizagem.

## Fluxo principal

```text
Professor cria e revisa o pacote
→ cria uma publicação com snapshot imutável
→ seleciona turmas ou estudantes
→ configura prazo, tentativas e feedback
→ estudante acessa, lê e responde
→ respostas são salvas automaticamente
→ sistema corrige questões objetivas
→ professor corrige respostas abertas
→ professor acompanha entregas e resultados básicos
```

## Publicações

A publicação preserva um snapshot do pacote pedagógico e da HQ. Alterações posteriores no material original não modificam silenciosamente o conteúdo já entregue aos estudantes.

Tipos iniciais:

- somente leitura;
- leitura com exercício;
- atividade;
- quiz;
- avaliação;
- pré-teste;
- pós-teste;
- reforço;
- desafio complementar.

Configurações:

- liberação e prazo;
- limite de tempo;
- quantidade máxima de tentativas;
- nota máxima;
- entrega atrasada e penalidade;
- ordem aleatória de questões ou alternativas;
- feedback imediato, após entrega, após prazo ou manual;
- política de exibição do gabarito;
- correção automática ou manual.

## Destinatários e acomodações

Uma publicação pode ser direcionada a:

- turma inteira;
- várias turmas;
- usuário específico;
- todos, exceto usuários selecionados;
- grupos pedagógicos internos.

Cada destinatário pode receber ajustes privados:

- prazo diferenciado;
- limite de tempo diferenciado;
- tentativas adicionais;
- liberação específica;
- configurações de acessibilidade.

## Área do estudante

Rotas principais:

```text
/aluno/atividades
/aluno/atividades/{assignment_id}
```

Recursos:

- atividades pendentes, em andamento e concluídas;
- leitor de HQ multipágina;
- salvamento automático;
- retomada de tentativa;
- envio final;
- resultado e feedback conforme política docente;
- notificações internas.

O gabarito e as orientações exclusivas do professor são removidos do payload enviado ao estudante.

## Questões e correção

Tipos implementados:

- múltipla escolha;
- verdadeiro ou falso;
- múltipla seleção;
- resposta curta;
- resposta numérica com tolerância;
- associação;
- ordenação;
- discursiva.

Questões objetivas recebem correção determinística. Questões discursivas entram na fila de correção manual.

## Acompanhamento do professor

Rotas principais:

```text
/publicacoes
/publicacoes/{assignment_id}
```

Indicadores básicos:

- quantidade de estudantes;
- não iniciados;
- em andamento;
- entregues;
- corrigidos;
- conclusão da turma;
- média provisória;
- tentativas por estudante;
- desempenho por questão;
- fila de correções manuais.

A Sprint 10 utilizará esses dados para Learning Analytics avançado.

## Segurança e privacidade

- isolamento por organização;
- acesso do estudante somente às próprias atividades e tentativas;
- professor limitado às organizações e turmas autorizadas;
- snapshots imutáveis;
- gabarito oculto até a política permitir;
- referências de tentativa e questão validadas em eventos de aprendizagem;
- acomodações individuais não expostas aos colegas;
- histórico de ações e eventos de aprendizagem.

## Estrutura de dados

Migration:

```text
0013_teacher_studio_canvas
→ 0014_learning_delivery
```

Tabelas:

- `material_assignments`;
- `assignment_recipients`;
- `assignment_questions`;
- `student_attempts`;
- `student_answers`;
- `learning_events`;
- `user_notifications`.

## API

A Sprint 09 acrescenta endpoints para:

- criar, editar, publicar, duplicar, encerrar e cancelar publicações;
- adicionar ou remover destinatários;
- configurar questões;
- visualizar como estudante;
- acompanhar progresso;
- liberar tentativa adicional;
- corrigir respostas manualmente;
- reabrir tentativa;
- listar atividades do estudante;
- iniciar ou retomar tentativa;
- salvar respostas;
- entregar;
- consultar resultados;
- registrar eventos de aprendizagem;
- consultar notificações.

## Próxima etapa

A Sprint 10 deverá implementar Learning Analytics:

- evolução individual e coletiva;
- desempenho por Pensamento Computacional e BNCC;
- análise de itens;
- alertas pedagógicos;
- recomendações de reforço;
- comparações entre atividades e turmas;
- exportação de dados.
