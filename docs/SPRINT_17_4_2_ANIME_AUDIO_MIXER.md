# Sprint 17.4.2 — Edição e mixagem de áudio

## Incremento entregue

O Anime Studio agora permite editar cada faixa de voz, música, efeito ou audiodescrição diretamente no mixer. A interface oferece forma de onda simplificada e controles para sincronização com cena, início, duração/corte, recorte inicial, volume, fade in, fade out e silenciamento.

Também é possível substituir o arquivo de áudio preservando a faixa canônica e seus vínculos. O novo arquivo passa pelo fluxo existente de upload e validação de mídia institucional.

## Reuso e governança

- Reutiliza `AnimeAudioTrack`, o endpoint `PATCH` existente e o escopo por organização.
- Reutiliza `InstitutionalAssetFile` para substituição do áudio.
- Mantém o fluxo de direitos de uso na inclusão de novas faixas.
- Não cria tabela ou coluna e não exige nova migration.

## Validação e rollback

Os contratos de schema cobrem cortes, fades, volume e mute. Os testes estáticos garantem reuso de ativos canônicos, validação de arquivo e isolamento por organização. O rollback funcional consiste em restaurar os valores anteriores da faixa ou substituir novamente o arquivo; o rollback de código não depende de downgrade de banco.
