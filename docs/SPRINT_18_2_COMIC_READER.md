# Sprint 18.2 — Leitor de HQ

## Objetivo

Completar a experiência de leitura de HQ do estudante com controles visuais e
assistivos persistentes, reutilizando o leitor, o manifesto, os checkpoints, as
preferências e a telemetria canônicos.

## Entrega

- zoom de 50% a 250%, com botões e controle deslizante;
- orientação automática, retrato ou paisagem;
- leitura por página, quadro, foco ou rolagem vertical contínua;
- modo leitor de tela com região viva e foco reforçado;
- exibição conjunta de texto alternativo e audiodescrição;
- narração TTS manual ou automática ao avançar;
- persistência das escolhas na preferência JSON já existente;
- adaptação responsiva da orientação em telas menores.

## Arquitetura

Não há nova tabela nem migration. `zoom_level` e `orientation` são campos
normalizados dentro de `comic_reader_preferences.preferences`, seguindo o
mesmo contrato dos demais recursos de acessibilidade. A narração usa as faixas
do manifesto quando possuem transcrição e mantém fallback para
`audio_description`, `alt_text`, descrição da cena e falas.

## Critérios de aceitação

1. O zoom e a orientação são restaurados após salvar as preferências.
2. A rolagem vertical apresenta todas as páginas em ordem.
3. O modo leitor de tela anuncia a mudança do conteúdo atual.
4. Audiodescrição e texto alternativo são identificados separadamente.
5. A narração automática pode ser desligada a qualquer momento.
6. Alto contraste e redução de movimento continuam funcionais.

## Rollback

Reverter o commit remove os novos controles e campos normalizados. Nenhum
downgrade Alembic é necessário porque não há alteração de esquema.
