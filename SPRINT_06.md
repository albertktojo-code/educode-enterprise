# Sprint 06 — Orquestração do Contexto RAG

## Objetivo

Transformar os resultados recuperados na Sprint 05 em um contexto pedagógico verificável, citável, seguro e revisável antes de qualquer geração narrativa.

## Entregas

- montagem de contexto vinculada ao planejamento pedagógico;
- seleção diversificada de trechos e remoção de duplicações próximas;
- fatos obrigatórios com confiança, tipo e códigos de citação;
- rastreabilidade entre fato, chunk, página e fonte;
- regras pedagógicas, narrativas, criativas, visuais, de segurança e acessibilidade;
- continuidade obrigatória entre quadros sem engessar a criatividade;
- autorização de humor, emoção, suspense e plot twists coerentes com pistas anteriores;
- isolamento entre instruções confiáveis e fontes educacionais não executáveis;
- detecção preliminar de conflitos entre afirmações;
- avaliação de relevância, cobertura, diversidade, rastreabilidade, consistência e segurança;
- revisão dos fatos, inclusão ou exclusão de fontes e aprovação docente;
- contrato estruturado e versão textual prontos para a Sprint 07.

## Migration

```text
0008_vector_retrieval
        ↓
0009_rag_context_orchestration (head)
```

## Página

```text
http://localhost:5173/contextos-rag
```

## Atualização preservando volumes

```powershell
docker compose down --remove-orphans
docker compose up --build
```

Não use `docker compose down -v`, pois esse comando remove os volumes de dados.
