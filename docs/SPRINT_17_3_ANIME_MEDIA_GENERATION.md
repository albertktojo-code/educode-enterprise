# Sprint 17.3 — Geracao de midia do Anime

## Entrega

- Solicitacoes de imagem, animacao, voz, sincronizacao labial, trilha e efeitos.
- Processamento assincrono na fila canonica `media_generation`.
- Idempotencia, retentativas, progresso e isolamento por organizacao.
- Estimativa e reserva de custo pela infraestrutura institucional de quotas.
- Revisao humana obrigatoria com aprovacao ou rejeicao auditada.
- Aba no Anime Studio para solicitar, acompanhar e revisar cada geracao.

## Criterios de aceite

1. Midias ligadas a cenas exigem uma cena do projeto e da organizacao atual.
2. Cada solicitacao informa o custo estimado antes do consumo da reserva.
3. Jobs repetidos sao idempotentes e respeitam limites simultaneos e financeiros.
4. Resultados concluidos permanecem pendentes ate decisao humana.
5. A decisao de revisao e registrada na auditoria consolidada.

## Banco de dados e rollback

A sprint reutiliza `background_jobs`, `resource_reservations`, cenas e ativos canonicos.
Nao ha migration. O rollback consiste em reverter rotas, servicos, interface e testes desta
entrega; nenhum schema ou dado precisa ser removido.
