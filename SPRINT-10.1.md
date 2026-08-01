# Sprint 10.1 — Biblioteca Institucional de Elementos

## Objetivo

Disponibilizar uma biblioteca visual institucional administrada exclusivamente por proprietários e administradores, com personagens, cenários, objetos e outros elementos reutilizáveis no Estúdio do Professor e no canvas.

## Entregas

- aba `/admin/biblioteca-elementos`, visível apenas para `owner` e `admin`;
- autorização também aplicada nas rotas do backend;
- catálogo de personagens, cenários, objetos, fundos, animais, veículos, móveis, roupas, acessórios, efeitos, balões, ícones, molduras, capas, layouts, paletas e logotipos;
- upload de PNG, JPG, WebP e PDF;
- validação de assinatura, tamanho, checksum e arquivos duplicados;
- elementos, variantes, arquivos e versões separados;
- categorias, subcategorias e tags;
- compatibilidade com HQ, anime, storyboard, quiz, jogo, impressão e vídeo;
- direitos autorais, atribuição, restrições e confirmação de autorização;
- fluxo: rascunho, revisão, aprovação, publicação, bloqueio, obsolescência e arquivamento;
- coleções e kits criativos;
- catálogo publicado somente para professores da mesma organização;
- auditoria e registro de utilização;
- armazenamento em volume Docker independente;
- download protegido dos arquivos administrativos e publicados.

## Personagens gerados em HQ

No editor de HQ, o professor pode salvar um personagem com nome em:

1. biblioteca do projeto;
2. biblioteca pessoal;
3. fila de aprovação institucional.

São preservados nome, descrição, personalidade, modo de falar, papel pedagógico, prompt visual, prompt negativo, características imutáveis e HQ/página/quadro de origem.

## Migration

`0016_learning_analytics -> 0017_institutional_asset_library`

## Novas variáveis

```env
INSTITUTIONAL_ASSET_STORAGE_VOLUME_NAME=educode-institutional-assets
INSTITUTIONAL_ASSET_STORAGE_PATH=/app/storage/institutional-assets
MAX_INSTITUTIONAL_ASSET_SIZE_MB=50
```
