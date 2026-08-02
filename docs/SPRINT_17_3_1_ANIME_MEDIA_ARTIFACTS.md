# Sprint 17.3.1 — Artefatos reais de midia

## Entrega

- Provedor interno de fallback que produz PNG, MP4 e WAV validos com FFmpeg.
- Persistencia dos arquivos na biblioteca institucional com checksum e versao.
- Preview protegido do resultado antes da revisao humana.
- Aprovacao conecta imagem/video a cena e voz/trilha/efeito ao mixer.
- Rejeicao preserva o artefato e seu historico sem associa-lo a producao.
- Identificacao explicita do provedor `educode_internal_ffmpeg`.

O fallback garante um fluxo funcional local. Adaptadores externos podem substituir a etapa de
geracao posteriormente sem alterar contratos, filas, revisao ou armazenamento.

## Banco de dados e rollback

A sprint reutiliza jobs, ativos, arquivos, versoes, cenas e faixas existentes. Nao ha migration.
O rollback remove o handler do worker e a associacao dos artefatos, sem excluir dados existentes.
