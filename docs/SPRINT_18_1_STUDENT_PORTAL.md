# Sprint 18.1 — Portal do Estudante

## Objetivo

Reunir a jornada do estudante em uma página inicial única, sem duplicar os
domínios canônicos de atividades, avaliações, HQs, animes, aprendizagem
adaptativa, progresso ou notificações.

## Entrega

- rota `/aluno` e atalho **Início** na navegação estudantil;
- resumo pessoal de pendências, conclusões, média e notificações não lidas;
- continuidade das atividades em andamento;
- prateleira com HQs e animes autorizados para o estudante;
- atalhos para progresso, trilha, avaliações e plano de apoio;
- carregamento resiliente com `Promise.allSettled`: uma falha parcial é
  informada sem esconder os demais dados disponíveis;
- estados de carregamento, vazio e erro, landmarks semânticos e layout
  responsivo.

## Arquitetura

O portal apenas compõe APIs existentes e autenticadas:

- `GET /student/assignments`;
- `GET /student/notifications`;
- `GET /analytics/student/progress`;
- `GET /comic-reader/releases`;
- `GET /anime-studio/publications`.

Não há nova tabela, modelo, router backend ou migration nesta sprint. O
isolamento por organização e as permissões continuam sob responsabilidade dos
endpoints canônicos.

## Critérios de aceitação

1. O estudante acessa `/aluno` pela navegação principal.
2. Atividades pendentes levam à experiência já existente.
3. HQs e animes levam aos leitores autorizados.
4. Falhas parciais são visíveis e não substituídas por dados fictícios.
5. O portal funciona em telas desktop e móveis e preserva navegação por
   teclado.

## Rollback

Reverter o commit da sprint remove a página, a rota, o item de menu e os
estilos. Como não há alteração de banco, nenhum downgrade Alembic é necessário.
