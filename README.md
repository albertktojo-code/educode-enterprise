# EduCode Enterprise 2.0 — Sprint 14

> Estado consolidado em evolução: versão `0.16.11.5`,
> Alembic `0054_delivery_model_sync` (head único). O histórico abaixo descreve
> a base da Sprint 14; consulte
> [`docs/STABILIZATION_2026_07_30.md`](docs/STABILIZATION_2026_07_30.md)
> para a auditoria de base e
> [`SPRINT_16_11_5.md`](SPRINT_16_11_5.md) para a evolução atual.

Versão consolidada das Sprints 01–13.3. Esta entrega acrescenta **Aprendizagem Adaptativa e Trilhas Personalizadas**, mantendo a infraestrutura distribuída, a IA transversal, o Núcleo de Avaliação Integrada, Learning Analytics e o Laboratório Estatístico.

## Regra pedagógica

> O EduCode recomenda. O professor decide. O estudante aprende. A plataforma mede e explica.

## Novidades da Sprint 14

- migration `0028_adaptive_learning`;
- mapa de domínio por habilidade BNCC e pilar de Pensamento Computacional;
- cálculo determinístico com peso, dificuldade, recência, consistência e confiança;
- evidências rastreáveis até avaliação, tentativa, resposta e questão;
- recomendações explicáveis e obrigatoriamente revisadas pelo professor;
- trilhas individuais, por turma e por grupos pedagógicos temporários;
- critérios de avanço com domínio mínimo, quantidade de evidências e etapas obrigatórias;
- revisão espaçada em ciclos configuráveis;
- área do professor em `/adaptativo`;
- área do estudante em `/aluno/minha-trilha`;
- auditoria completa das decisões adaptativas;
- ausência de rankings públicos ou rótulos permanentes.

## Atualização preservando dados

Copie o `.env` funcional da Sprint 13.3 e execute:

```powershell
docker compose down --remove-orphans
docker compose up -d db redis
docker compose run --rm backend python -m app.operations.preflight
docker compose run --rm backend python -m app.operations.migration_check --json
docker compose run --rm backend alembic upgrade head
docker compose up -d --build
docker compose run --rm backend alembic current
docker compose ps
```

Resultado esperado:

```text
0028_adaptive_learning (head)
```

Não execute `docker compose down -v`.

## Acessos principais

- Frontend: `http://localhost:5173`
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Aprendizagem adaptativa: `http://localhost:5173/adaptativo`
- Recomendações: `http://localhost:5173/adaptativo/recomendacoes`
- Trilhas: `http://localhost:5173/adaptativo/trilhas`
- Minha trilha: `http://localhost:5173/aluno/minha-trilha`
- Infraestrutura e DR: `http://localhost:5173/admin/infraestrutura`

Consulte `SPRINT-14.md`, `SPRINT-13.3.md`, `INFRASTRUCTURE.md`, `OBSERVABILITY.md`, `OPERATIONS.md` e `SECURITY.md`.
