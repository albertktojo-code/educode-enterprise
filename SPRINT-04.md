> **Nota:** esta entrega foi ampliada pela Sprint 04.1. Consulte `SPRINT-04.1.md` para páginas, capítulos e revisão docente.

# Sprint 04 — Documentos, PDFs e preparação para RAG

## Objetivo

Criar uma camada profissional de ingestão documental sem dependência da OpenAI,
armazenando PDFs e extraindo texto para uso posterior no pipeline RAG.

## Backend

### Modelo `Document`

- organização proprietária;
- usuário responsável pelo upload;
- projeto opcional;
- nome original;
- chave segura de armazenamento;
- MIME type e tamanho;
- checksum SHA-256;
- status de processamento;
- número de páginas;
- texto extraído;
- mensagem de erro;
- datas de criação, atualização e processamento.

### Endpoints

```http
GET    /api/v1/documents
POST   /api/v1/documents/upload
GET    /api/v1/documents/{document_id}
GET    /api/v1/documents/{document_id}/text
GET    /api/v1/documents/{document_id}/download
PATCH  /api/v1/documents/{document_id}
POST   /api/v1/documents/{document_id}/process
DELETE /api/v1/documents/{document_id}
```

### Segurança

- Todas as consultas são filtradas por `organization_id`.
- `owner`, `admin` e `teacher` podem enviar, processar e vincular PDFs.
- `member` possui acesso somente para consulta e download.
- Apenas `owner` e `admin` podem excluir documentos.
- Caminhos físicos são resolvidos sob uma raiz controlada, impedindo path traversal.
- Arquivos são validados por extensão, MIME type e assinatura `%PDF-`.

## Frontend

A nova página **Documentos** oferece:

- upload de PDF;
- vínculo com projeto;
- processamento automático opcional;
- busca por nome e checksum;
- filtros de status;
- visualização do texto extraído;
- reprocessamento;
- download autenticado;
- alteração de projeto;
- exclusão;
- métricas da base documental.

## Fora do escopo

Nesta sprint não são criados chunks nem embeddings. Essas operações fazem parte
da Sprint 05, evitando acoplamento prematuro entre ingestão e recuperação vetorial.
