# Sprint 05 — Indexação hierárquica, pgvector e busca híbrida

## Objetivo

Transformar fontes pedagógicas confirmadas em um índice rastreável e pesquisável,
sem gerar ainda o material final. O resultado da Sprint 05 é um mecanismo capaz
de localizar o conteúdo correto no documento, capítulo, unidade e página corretos.

## Fontes indexáveis

- unidades pedagógicas confirmadas, vinculadas a capítulos confirmados;
- páginas com texto válido extraído do PDF;
- textos e histórias escritos pelo professor;
- instruções estruturadas de projetos pedagógicos;
- fontes híbridas associadas ao Estúdio Pedagógico.

## Chunking hierárquico

A hierarquia preservada é:

```text
Organização
└── Documento ou fonte textual
    └── Capítulo
        └── Unidade pedagógica
            └── Página
                └── Chunk
```

O chunker:

- preserva parágrafos sempre que possível;
- evita cortes arbitrários no meio das frases;
- registra página inicial e final;
- mantém `source_order` e `chunk_index`;
- usa sobreposição configurável;
- produz checksum determinístico;
- estima caracteres e tokens;
- identifica possíveis instruções maliciosas presentes nas fontes.

Configuração padrão:

```env
RETRIEVAL_CHUNK_TARGET_CHARS=1000
RETRIEVAL_CHUNK_OVERLAP_CHARS=160
RETRIEVAL_CHUNK_MIN_CHARS=200
RETRIEVAL_DEFAULT_TOP_K=8
```

## Embeddings mock

Provider inicial:

```text
provider: mock
model: deterministic-hash-v1
dimension: 384
```

O mesmo texto sempre produz o mesmo vetor. A interface foi isolada para permitir
substituição futura por provider local ou externo sem alterar o domínio.

## Busca

### Semântica

Usa distância por cosseno no pgvector.

### Textual

Usa `tsvector`, `websearch_to_tsquery` e ranking textual do PostgreSQL.

### Híbrida

Combina os rankings vetorial e textual por Reciprocal Rank Fusion — RRF.

Os filtros disponíveis incluem:

- organização atual;
- documento;
- capítulo;
- unidade pedagógica;
- fonte de projeto;
- processo de indexação.

## Ordem pedagógica

A resposta de busca possui duas visões:

1. ranking de relevância;
2. contexto ordenado pela posição original da fonte.

Isso permite recuperar os melhores trechos sem enviar conceitos embaralhados para
a Sprint 06. Cada item do contexto inclui rótulo de citação e ordem original.

## Segurança

O texto recuperado deve ser tratado como fonte pedagógica não executável. O sistema
marca padrões como “ignore as instruções anteriores” e mantém o trecho disponível
para revisão, sem interpretá-lo como comando.

## Versionamento e desatualização

Cada indexação registra:

- checksum da fonte;
- versão do chunker;
- provider e modelo de embedding;
- revisão da indexação;
- quantidade de chunks ativos;
- data da indexação.

Ao detectar alteração na fonte, o job muda automaticamente para `stale`. A
reindexação cria uma nova revisão e desativa os chunks anteriores somente após a
nova preparação começar dentro de uma transação segura.

## Novas tabelas

### `retrieval_index_jobs`

Estado, progresso, configuração, checksum e revisão de cada fonte indexada.

### `document_chunks`

Conteúdo hierárquico, páginas, ordem, embedding `vector(384)`, vetor textual,
metadados, segurança e versão.

### `retrieval_feedback`

Avaliação manual dos resultados como relevante, parcialmente relevante ou
irrelevante.

## Nova migration

```text
Revision ID: 0008_vector_retrieval
Revises: 0007_creative_library
```

Índices criados:

- B-tree para isolamento e filtros;
- GIN para busca textual;
- HNSW com `vector_cosine_ops` para evolução de escala;
- busca exata continua disponível no laboratório.

## Novas rotas

```http
GET    /api/v1/retrieval/index-jobs
POST   /api/v1/retrieval/index-learning-unit/{learning_unit_id}
POST   /api/v1/retrieval/index-generation-source/{generation_source_id}
GET    /api/v1/retrieval/chunks
DELETE /api/v1/retrieval/index-jobs/{job_id}/chunks
POST   /api/v1/retrieval/search
POST   /api/v1/retrieval/feedback
GET    /api/v1/retrieval/stats
```

## Novas telas

```text
/indexacao
/laboratorio-rag
```

### Indexação Pedagógica

- unidades confirmadas;
- textos e instruções do professor;
- configuração do chunking;
- indexação e reindexação;
- inspeção dos chunks;
- revisão e alertas de segurança;
- remoção do índice sem apagar a fonte original.

### Laboratório RAG

- comparação entre busca semântica, textual e híbrida;
- filtros por fonte;
- scores separados;
- explicação do resultado;
- avaliação manual de relevância;
- contexto final reorganizado na ordem da fonte.

## Validações executadas

- Ruff: aprovado;
- mypy estrito: aprovado;
- pytest: 25 testes aprovados;
- TypeScript/Vite: aprovado;
- ESLint: aprovado;
- Alembic: oito migrations encadeadas;
- OpenAPI: 62 caminhos carregados.

## Limites desta sprint

A Sprint 05 não gera HQ, quiz ou roteiro. Ela recupera e organiza as fontes. A
Sprint 06 montará o contexto RAG com citações, regras pedagógicas e separação entre
fatos obrigatórios e liberdade criativa.
