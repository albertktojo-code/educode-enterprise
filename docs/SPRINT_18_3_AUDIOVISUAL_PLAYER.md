# Sprint 18.3 — Player audiovisual

## Objetivo

Completar a reprodução dos animes publicados com velocidade configurável,
qualidade adaptativa, transcrição navegável e retomada segura no dispositivo.

## Entrega

- velocidades de 0,75× a 2×;
- qualidade automática baseada na largura da tela, densidade de pixels,
  economia de dados e tipo efetivo da conexão;
- seleção manual de cada resolução publicada;
- progresso visual atualizado durante a reprodução;
- retomada automática por projeto e revisão publicada;
- salvamento durante reprodução, pausa e conclusão;
- transcrição navegável, com salto para o instante selecionado;
- destaque específico dos trechos de audiodescrição;
- preservação das legendas WebVTT e dos controles nativos acessíveis.

## Persistência e privacidade

Nesta etapa incremental, a posição é armazenada no `localStorage` do
dispositivo e separada por `project_id` e `render_revision`. Isso evita criar
uma fonte paralela de progresso no backend antes do domínio de eventos do
estudante. A posição não é compartilhada entre dispositivos; essa limitação é
exibida ao estudante.

## Critérios de aceitação

1. Alterar a velocidade afeta imediatamente o vídeo atual.
2. O modo automático escolhe uma resolução disponível compatível com o
   dispositivo e a conexão.
3. Reabrir o mesmo vídeo retoma uma posição válida, exceto nos primeiros ou
   últimos cinco segundos.
4. Trocar a revisão publicada não reutiliza progresso incompatível.
5. Selecionar um trecho da transcrição move o vídeo e inicia a reprodução.
6. Trechos de audiodescrição são identificáveis sem depender apenas de cor.

## Rollback

Reverter o commit restaura o player anterior. Não há migration nem alteração
de esquema para reverter. Entradas locais antigas tornam-se inativas e podem
ser removidas pelos controles de dados do navegador.
