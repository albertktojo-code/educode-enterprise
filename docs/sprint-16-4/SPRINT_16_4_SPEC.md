# Sprint 16.4 - Especificação

## Objetivo

Criar um fluxo editorial rastreável para que HQs produzidas no EduCode sejam revisadas, aprovadas e publicadas com segurança.

## Fluxo principal

1. O autor abre uma sessão de revisão.
2. Revisores são atribuídos por especialidade.
3. Comentários são vinculados a páginas, quadros ou camadas.
4. Alterações solicitadas são registradas e respondidas.
5. Checklists pedagógicos e técnicos são concluídos.
6. O fluxo calcula o quórum de aprovação.
7. Uma versão aprovada gera um release imutável.
8. O release é publicado para públicos autorizados.
9. Publicações podem ser retiradas sem apagar o histórico.

## Segurança editorial

- releases publicados não são editados;
- uma correção gera novo release;
- decisões registram o hash da versão revisada;
- rejeições e pedidos de mudança exigem justificativa;
- dados de outra organização não são acessíveis;
- publicação em catálogo público depende de permissão institucional;
- nenhuma aprovação automática substitui a decisão humana.
