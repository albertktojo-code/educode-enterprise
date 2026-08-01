# Arquitetura — Sprint 15

## Modulo backend

`app.assessment_hub`

- `models.py`: persistencia isolada por organizacao;
- `schemas.py`: contratos Pydantic;
- `services/scoring.py`: correcao deterministica;
- `services/assembly.py`: montagem simulada e explicavel;
- `services/analytics.py`: dificuldade observada;
- `services/instruments.py`: consolidacao por dimensoes;
- `router.py`: API REST sob `/api/v1/assessment-hub`.

## Migration

Revision: `0031_assessment_hub`.

O instalador detecta o head atual do projeto e atualiza `down_revision` antes da copia. O identificador possui menos de 32 caracteres.

## Integracao

A Sprint 15 reutiliza o contexto de organizacao, autenticacao, banco assincrono, auditoria e Docker Compose do EduCode. Nao cria notas ou trilhas paralelas.
