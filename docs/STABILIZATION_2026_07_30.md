# Estabilização do EduCode — 30/07/2026

## Resultado

O repositório consolidado foi estabilizado sobre a versão `0.16.11.4`.
A aplicação permanece com arquitetura única para avaliações:

- Assessment Hub: itens, versões, tentativas e respostas;
- Assessment Delivery: publicações, públicos, sessões, itens de sessão,
  autosave, tempo e submissão;
- HQ: vínculo narrativo, leitura e estado de navegação, sem criar tentativas ou
  respostas paralelas.

O diretório recebido não contém metadados `.git`. Por isso, não existe baseline
Git para `status`, diff ou restauração. Os backups de sprint existentes foram
preservados e um dump PostgreSQL adicional foi criado antes da migration.

## Correções funcionais

### OpenAPI

A geração do schema falhava por um import ausente de
`HQLearningAnalyticsGenerate`. O import foi restaurado e há teste de regressão
que materializa `app.openapi()`.

### Experiência do estudante em HQ

O fluxo deixou de chamar o endpoint docente de simulação de correção. Agora:

1. o manifesto GET é somente leitura;
2. o estudante inicia explicitamente a tentativa;
3. o backend valida publicação, janela e público elegível;
4. públicos `STUDENT`, `CLASSROOM` e `GROUP` verificam vínculo na organização;
5. `CLASS` é aceito apenas como alias legado e persistido como `CLASSROOM`;
6. a sessão e seus itens são criados no Assessment Delivery;
7. cada resposta usa o autosave canônico, com sequência e checksum;
8. a submissão grava respostas e resultado no Assessment Hub;
9. contagem respondida e progresso de atividades são derivados do estado
   canônico, não do payload do navegador;
10. respostas que exigem revisão permanecem sob decisão humana.

O manifesto não cria estado nem tentativa. A tentativa só é aberta após a ação
“Iniciar experiência”, evitando iniciar o cronômetro por uma leitura GET.

### Segurança e isolamento

- endpoints do estudante exigem papel de estudante/membro;
- o alvo informado no início da sessão precisa pertencer à publicação;
- o estudante precisa estar no público direto, na turma ou no grupo ativo;
- o usuário precisa ter membership ativa na organização;
- janelas específicas do público são verificadas;
- a publicação canônica vinculada à HQ é consultada com `organization_id`;
- o frontend continua usando o cliente HTTP central autenticado.

### Compatibilidade

`score_proxy` foi restaurado como API de compatibilidade do domínio de
intervenções. O cálculo longitudinal mais novo continua usando
`comparable_outcome`.

## Migration 0054

`0054_delivery_model_sync` deriva do head real
`0053_hq_learning_analytics` e adiciona somente 11 colunas que já existiam no
ORM, mas faltavam no banco:

- `material_assignments`: `assessment_version_id`;
- `assignment_questions`: `question_bank_item_id`, `source_type`,
  `source_metadata`, `item_version`, `item_snapshot_checksum`, `is_annulled`,
  `annulment_reason`;
- `student_attempts`: `assessment_version_id`, `grading_revision`,
  `recalculated_at`.

A migration também cria três FKs e três índices explícitos. Não cria tabelas ou
domínios paralelos. Upgrade, downgrade para `0053` e novo upgrade foram
executados com sucesso.

## Backup e rollback

Dump anterior à migration:

`/.sprint-backups/stabilization-0054/pre_0054_delivery_model_sync.dump`

- tamanho: `1.506.134` bytes;
- SHA-256:
  `5808C1D0AC83869BF1A9E1AD5D2A27B64D30AB288ABAE0DFC17990893E362731`.

Rollback normal da migration:

```powershell
docker-compose exec -T backend alembic downgrade 0053_hq_learning_analytics
```

O dump é a contingência adicional. Uma restauração integral deve ser feita em
janela de manutenção, após preservar o estado corrente, porque substitui dados
posteriores ao backup.

## Validações executadas

- compilação dos arquivos Python alterados: sucesso;
- OpenAPI: HTTP 200;
- suíte completa do backend: `440 passed`, `1 skipped`;
- skip: contrato frontend não montado no container do backend;
- aviso conhecido: depreciação Starlette/TestClient para `httpx2`;
- TypeScript + Vite: sucesso, 221 módulos transformados;
- aviso conhecido: bundle principal de aproximadamente 882 kB;
- `docker-compose config --quiet`: sucesso, com aviso local de permissão no
  arquivo global `~/.docker/config.json`;
- build das imagens backend e frontend: sucesso;
- `alembic current`: `0054_delivery_model_sync (head)`;
- `alembic heads`: um único head;
- downgrade `0054 -> 0053`: sucesso;
- upgrade `0053 -> 0054`: sucesso;
- backend, PostgreSQL e Redis: healthy;
- `/api/v1/health/live`: versão `0.16.11.4`;
- `/api/v1/health/ready`: banco, Redis e storage healthy;
- frontend: HTTP 200.

## Drift residual

Depois da 0054, `alembic check` não detecta mais `add_column`. Ainda existem
diferenças históricas de metadados:

- `modify_type`: 170;
- `modify_nullable`: 2;
- `add_index`: 512;
- `remove_index`: 388;
- `remove_constraint`: 20.

Essas diferenças atravessam muitos domínios e incluem equivalências de tipo,
nomenclatura e índices já existentes. Elas não foram aplicadas em massa porque
uma migration autogerada desse porte seria arriscada. Devem ser classificadas
por domínio em uma tarefa separada, com comparação de SQL efetivo e plano de
lock/rollback.

## Riscos restantes

- não há teste E2E com navegador, usuário estudante e publicação real
  previamente preparada; os contratos, serviços, build e APIs canônicas foram
  validados separadamente;
- o bundle frontend deve ser particionado por rotas/features;
- o drift histórico de tipos, índices e constraints continua exigindo
  saneamento incremental;
- a ausência de `.git` reduz a rastreabilidade de origem; não remover os
  backups até o repositório ser colocado sob controle de versão.
