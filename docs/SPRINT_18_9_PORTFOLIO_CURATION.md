# Sprint 18.9 — Curadoria e reflexão autoral

## Produtos e fonte de verdade

- **EduCode Credentials** mantém a seleção e a reflexão do estudante.
- **EduCode Assess/Delivery** permanece como fonte da atividade, tentativa e resultado.
- O portfólio referencia a tentativa concluída; não copia respostas nem altera notas.

## Incremento entregue

- seleção idempotente de atividades concluídas para o portfólio;
- snapshot rastreável do título, tipo, tentativa e percentual no momento da curadoria;
- reflexão privada de até 2.000 caracteres, com revisão incremental;
- remoção da curadoria sem apagar a evidência acadêmica original;
- isolamento por organização e autoria do estudante em todas as operações;
- auditoria consolidada para seleção, edição de reflexão e remoção;
- interface responsiva com loading, erro, estado vazio e mensagens por `aria-live`.

## Banco, instalação e rollback

A migration `0057_student_portfolio` cria somente `student_portfolio_entries`, baseada no
head real `0056_anime_audiovisual`. Os testes de código devem passar antes de qualquer
`alembic upgrade`. O downgrade remove exclusivamente a tabela e seu índice; atividades,
tentativas e resultados permanecem intactos.

## Limites

- reflexões permanecem privadas ao estudante nesta versão;
- produções do Studio exigirão vínculo canônico de autoria em incremento posterior;
- certificados exigirão emissão, verificação e revogação próprias e não são simulados.

## Critérios de aceite

- apenas tentativa `submitted` ou `graded` do próprio estudante pode ser selecionada;
- a mesma atividade não gera entradas duplicadas;
- professor ou usuário de outra organização não acessa a curadoria;
- editar ou remover uma entrada nunca modifica a tentativa original;
- toda mutação gera evento na auditoria consolidada.
