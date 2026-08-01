# Prompt inicial para continuar o EduCode Enterprise no Codex

Você está trabalhando no repositório consolidado do **EduCode Enterprise 2.0**.

Leia primeiro, nesta ordem:

1. `AGENTS.md`;
2. `README.md`;
3. `docker-compose.yml`;
4. `.env.example`;
5. migrations do Alembic;
6. módulos backend;
7. registro de rotas frontend;
8. testes existentes;
9. relatórios das últimas sprints.

## Contexto

O projeto evoluiu por sprints incrementais. A partir da Sprint 16.3 foram
implementadas biblioteca visual, revisão e publicação de HQs, leitor,
acessibilidade, Analytics, intervenções, governança, editor visual, narrativa
multipágina, balões, atividades pós-HQ, correção, aplicação para turmas,
experiência digital do estudante e Analytics pós-HQ.

O código instalado no repositório é a fonte de verdade. Não assuma que nomes,
tabelas ou migrations descritos em documentos estão exatamente iguais ao
estado atual.

## Sua primeira tarefa

Faça uma auditoria completa, sem alterar arquivos inicialmente.

Apresente:

1. estrutura real do backend;
2. estrutura real do frontend;
3. head atual do Alembic;
4. quantidade de heads;
5. tabelas e modelos dos domínios principais;
6. routers e rotas;
7. sistema de autenticação e RBAC;
8. sistema de auditoria;
9. integração com Assessment Hub;
10. integração com Assessment Delivery;
11. integração com Assessment Review;
12. módulos adaptativos e de intervenção;
13. estrutura das HQs;
14. leitor, acessibilidade e Analytics;
15. testes disponíveis;
16. comandos corretos para build e validação;
17. duplicações ou inconsistências;
18. riscos para a próxima sprint.

## Regras obrigatórias

- Não criar estruturas paralelas.
- Reutilizar os domínios canônicos.
- Toda consulta deve respeitar `organization_id`.
- Toda escrita sensível deve respeitar RBAC e auditoria.
- A IA deve manter revisão humana.
- Não editar migration já aplicada.
- Não criar nova migration antes de confirmar `alembic current` e
  `alembic heads`.
- Não usar `fetch` sem o cliente autenticado do frontend.
- Não afirmar que testes passaram sem executá-los.
- Não usar mocks silenciosos em produção.
- Não modificar arquivos ainda nesta primeira etapa.

## Comandos iniciais sugeridos

Execute apenas comandos seguros de leitura e diagnóstico:

```powershell
git status
git branch --show-current
docker compose config --quiet
docker compose ps
docker compose run --rm backend alembic current
docker compose run --rm backend alembic heads
```

Pesquise também:

```text
organization_id
append_domain_audit
get_current_user
require_role
AssessmentPublication
QuestionItem
QuestionVersion
ReviewRubric
HQEditorPage
HQActivityBinding
HQStudentExperienceState
```

## Formato da resposta

Entregue:

### Estado atual
Resumo do repositório e da arquitetura encontrada.

### Hierarquia real
Domínios, dependências e responsabilidades.

### Alembic
Head, cadeia e riscos.

### Duplicações
Estruturas equivalentes ou conflitantes.

### Testes
O que existe, o que executou e o resultado real.

### Próxima ação recomendada
Plano de implementação sem ainda alterar o código.

Pare após a auditoria e aguarde aprovação para implementar.
