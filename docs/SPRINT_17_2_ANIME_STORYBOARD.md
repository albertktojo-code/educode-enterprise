# Sprint 17.2 â€” Storyboard do Anime

## Entrega

- Conversao idempotente de uma HQ gerada em cenas do Anime Studio.
- Timeline ordenada com duracao estimada por quadro.
- Enquadramento, movimento de camera e transicao preservados no modelo canonico de cena.
- Continuidade narrativa, estados, acessibilidade e objetivos pedagogicos copiados da HQ.
- Isolamento por organizacao, RBAC de editor e auditoria consolidada.

## Criterios de aceite

1. Uma HQ da organizacao atual pode ser importada pelo seu UUID.
2. Cada quadro novo gera exatamente uma cena, mantendo pagina e quadro de origem.
3. Repetir a importacao nao duplica cenas ja sincronizadas.
4. HQs de outra organizacao nao sao reveladas nem importadas.
5. A tela mostra duracao, enquadramento, camera e transicao na timeline.

## Banco de dados e rollback

A sprint reutiliza `anime_scenes` e os campos JSON canonicos existentes. Nao ha migration.
O rollback consiste em reverter o endpoint, a interface e os testes desta entrega; nenhum dado
ou schema precisa ser removido.
