# Sprint 04.1 — Estruturação de PDFs por páginas e capítulos

Esta revisão conclui a base documental antes da implementação de chunking,
pgvector e RAG.

## Objetivo

Garantir que toda geração futura seja baseada em uma origem controlada:

```text
Documento → capítulo confirmado → páginas → chunks → material educacional
```

O EduCode não deverá enviar o texto integral e desestruturado de um livro para a
IA. O professor primeiro revisará os capítulos e intervalos de páginas.

## Funcionalidades

### Extração página a página

Cada página é persistida separadamente em `document_pages`, com:

- número da página;
- texto nativo;
- quantidade de caracteres;
- quantidade de imagens;
- método de extração;
- classificação da página;
- estado de OCR.

### Classificação de páginas

- `textual`: texto nativo suficiente;
- `mixed`: pouco texto e presença de imagens;
- `scanned`: imagem sem texto nativo;
- `empty`: sem texto nem imagem detectável.

As páginas mistas ou escaneadas recebem `ocr_status=required`. A execução real
do OCR permanece desacoplada e será conectada em uma etapa posterior.

### Detecção de capítulos

A detecção utiliza, nesta ordem:

1. sumário/bookmarks nativos do PDF;
2. títulos explícitos como Capítulo, Unidade, Módulo ou Seção;
3. títulos numerados;
4. linhas curtas em caixa alta;
5. capítulo único de fallback quando não houver estrutura detectável.

Cada capítulo registra método de detecção e índice de confiança.

### Revisão docente

Na rota `/documentos/:documentId`, usuários `owner`, `admin` e `teacher` podem:

- corrigir título;
- ajustar página inicial e final;
- adicionar resumo;
- reorganizar capítulos;
- criar capítulo manual;
- excluir capítulo;
- confirmar ou reabrir para revisão;
- detectar novamente preservando capítulos manuais e confirmados;
- refazer toda a estrutura quando necessário.

Capítulos confirmados não podem se sobrepor.

### Rastreabilidade preparada

O endpoint de texto do capítulo retorna:

- capítulo selecionado;
- texto concatenado;
- quantidade de caracteres;
- páginas de origem.

Esses dados serão utilizados pela Sprint 05 para criar chunks ligados a um
capítulo e às páginas corretas.

## Migration

```text
0004_documents -> 0005_document_structure (head)
```

Novas tabelas:

- `document_pages`;
- `document_chapters`.

Novos enums PostgreSQL:

- `document_page_kind`;
- `text_extraction_method`;
- `ocr_status`;
- `chapter_detection_method`.

## Atualização de uma instalação existente

Não remova os volumes.

```powershell
docker compose down --remove-orphans
docker compose up --build
```

O backend executará `alembic upgrade head` automaticamente.

Os documentos enviados antes desta versão continuarão cadastrados, mas devem
ser reprocessados na tela de estruturação para preencher páginas e capítulos.

## Novos endpoints

```http
GET    /api/v1/documents/{document_id}/structure-summary
GET    /api/v1/documents/{document_id}/pages
GET    /api/v1/documents/{document_id}/pages/{page_number}
GET    /api/v1/documents/{document_id}/chapters
POST   /api/v1/documents/{document_id}/chapters
POST   /api/v1/documents/{document_id}/chapters/detect
GET    /api/v1/documents/{document_id}/chapters/{chapter_id}/text
PATCH  /api/v1/documents/{document_id}/chapters/{chapter_id}
DELETE /api/v1/documents/{document_id}/chapters/{chapter_id}
```

## Fora do escopo desta revisão

- OCR real;
- unidades pedagógicas;
- chunking;
- embeddings;
- pgvector;
- geração de HQ, quiz, jogos ou anime.

Esses recursos serão implementados sobre a estrutura confirmada nesta sprint.
