# Sprint 04.2 — Planejamento pedagógico e Biblioteca Criativa

## Objetivo

Concluir a arquitetura anterior ao RAG e à geração final de materiais,
permitindo que o professor defina conteúdo, fontes, disciplinas, pilares de
Pensamento Computacional, objetivos, avaliação, personagens, cenários, estilos,
regras criativas e sequência didática.

## Modos de origem

- `document`: PDF, capítulo e unidade pedagógica;
- `ai`: tema e objetivos, usando IA mock;
- `teacher_text`: história ou roteiro escrito pelo professor;
- `hybrid`: combinação de PDF, texto docente, instruções e IA mock.

## Pilares de Pensamento Computacional

- `abstraction`;
- `decomposition`;
- `pattern_recognition`;
- `algorithms`.

## Níveis cognitivos

- `remember`;
- `understand`;
- `apply`;
- `analyze`;
- `evaluate`;
- `create`.

## Novas entidades da revisão consolidada

### `creative_items`

Cadastro unificado de personagem, cenário ou estilo.

### `creative_assets`

Imagens e PDFs de referência, com checksum, função do arquivo, página do PDF e
indicação de referência principal.

### `creative_versions`

Snapshot estruturado criado a cada edição do item criativo.

### `generation_project_creative_items`

Vínculo entre projetos e personagens, cenários ou estilos.

### `creative_bibles`

Bíblia Criativa Pedagógica do projeto.

### `teaching_sequences`

Sequência didática vinculada opcionalmente ao projeto.

### `teaching_sequence_items`

Etapas da sequência, material, objetivo, pilares, duração e papel avaliativo.

## Campos adicionados a `generation_projects`

- `cognitive_levels`;
- `measurable_objectives`;
- `evaluation_plan`;
- `author_credit_settings`.

## Nova migration

```text
Revision ID: 0007_creative_library
Revises: 0006_pedagogical_planning
```

## Novas rotas

```http
GET    /api/v1/creative/catalog
GET    /api/v1/creative/items
POST   /api/v1/creative/items
GET    /api/v1/creative/items/{creative_item_id}
PATCH  /api/v1/creative/items/{creative_item_id}
DELETE /api/v1/creative/items/{creative_item_id}

POST   /api/v1/creative/items/{creative_item_id}/assets
GET    /api/v1/creative/assets/{asset_id}/download
DELETE /api/v1/creative/assets/{asset_id}

GET    /api/v1/creative/generation-projects/{id}/items
PUT    /api/v1/creative/generation-projects/{id}/items
GET    /api/v1/creative/generation-projects/{id}/bible
PUT    /api/v1/creative/generation-projects/{id}/bible

GET    /api/v1/teaching-sequences
POST   /api/v1/teaching-sequences
GET    /api/v1/teaching-sequences/{sequence_id}
PATCH  /api/v1/teaching-sequences/{sequence_id}
DELETE /api/v1/teaching-sequences/{sequence_id}
```

## Uploads da Biblioteca Criativa

Formatos aceitos:

- PNG;
- JPG/JPEG;
- WebP;
- PDF.

O sistema valida extensão, MIME type, assinatura do arquivo, tamanho e checksum.

## Direitos e privacidade

Todo item criativo registra:

- organização;
- usuário criador;
- nome do criador no momento do cadastro;
- autor original;
- licença e restrições;
- confirmação de direitos;
- visibilidade;
- histórico de versões.

## Avaliação futura

A Sprint 04.2 não executa teste t, ANOVA ou outros testes. Ela registra:

- desenho da avaliação;
- variável dependente pretendida;
- grupos ou momentos;
- objetivos mensuráveis;
- níveis cognitivos;
- etapas que funcionarão como pré-teste, intervenção, pós-teste ou follow-up.

Esses dados serão consumidos pelo módulo de respostas e análise estatística em
sprints futuras.

## Validações executadas

- Ruff: aprovado;
- mypy estrito: aprovado;
- pytest: 18 testes aprovados;
- TypeScript/Vite: aprovado;
- ESLint: aprovado;
- Alembic: sete migrations encadeadas;
- OpenAPI: 54 caminhos carregados.
