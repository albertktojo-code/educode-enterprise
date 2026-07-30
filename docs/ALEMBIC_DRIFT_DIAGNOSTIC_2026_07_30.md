# Diagnóstico do drift do Alembic — 2026-07-30

## Escopo

Este diagnóstico compara o metadata SQLAlchemy carregado por
`backend/alembic/env.py` com o PostgreSQL local. A inspeção foi somente leitura:
nenhuma migration foi criada, aplicada, revertida ou marcada com `stamp`.

Baseline Git usado na análise:

- branch: `main`;
- commit: `79d4f12`;
- versão da aplicação: `0.16.11.5`;
- head instalado: `0054_delivery_model_sync`;
- head do repositório: `0054_delivery_model_sync`;
- quantidade de heads: 1.

O banco e o metadata possuem o mesmo conjunto funcional de tabelas e colunas.
O `alembic check` não propõe `add_table`, `remove_table`, `add_column` nem
`remove_column`.

## Resultado consolidado

A API de autogeração do Alembic encontrou 546 operações:

| Operação | Quantidade | Interpretação inicial |
| --- | ---: | --- |
| `add_index` | 256 | 181 renomes aparentes, 1 troca constraint/índice e 74 índices candidatos |
| `remove_index` | 194 | 181 renomes aparentes e 13 índices existentes não descritos no metadata |
| `modify_type` | 85 | todas propõem `JSONB -> JSON` |
| `remove_constraint` | 10 | constraints de unicidade existentes não representadas corretamente |
| `modify_nullable` | 1 | `material_assignments.package_id`: banco `NOT NULL`, modelo nullable |

Os números brutos extraídos do texto de `alembic check` aparecem duplicados
porque a lista completa é emitida em `ERROR` e novamente em `FAILED`. Os totais
acima foram obtidos diretamente de `produce_migrations(...).upgrade_ops` e
contam cada operação uma única vez.

## 1. Tipos JSONB versus JSON

As 85 alterações de tipo, distribuídas por 47 tabelas, têm exatamente o mesmo
padrão:

```text
PostgreSQL instalado: JSONB
metadata SQLAlchemy:  JSON
```

Não há evidência de que converter essas colunas para `JSON` seja uma mudança
funcional desejada. A conversão perderia as características próprias de JSONB e
pode afetar operadores, índices e planos de consulta.

Tabelas mais afetadas:

- `generation_projects`: 9 colunas;
- `comic_panels`: 7;
- `creative_bibles`, `generated_comics` e `release_validation_runs`: 4 cada;
- `adaptive_path_steps` e `restore_entity_jobs`: 3 cada;
- `adaptive_learning_profiles`, `adaptive_model_versions`,
  `adaptive_recommendations`, `comic_edit_operations`,
  `comic_generation_runs`, `diagnostic_runs`, `disaster_recovery_runs`,
  `infrastructure_clusters`, `object_storage_targets`, `rag_context_conflicts`
  e `rag_contexts`: 2 cada;
- outras 30 tabelas: 1 coluna cada.

Diagnóstico: drift de representação do modelo. O saneamento deve alinhar os
modelos PostgreSQL a `JSONB` ou introduzir uma comparação de tipos
explicitamente testada. Não deve converter o banco para `JSON` por
autogeração.

## 2. Índices com nomes divergentes

Existem 181 especificações com a mesma tabela, mesmas colunas e mesmo atributo
de unicidade nos dois lados, mas com nomes diferentes. Cada divergência gera
um `remove_index` seguido de um `add_index`, totalizando 362 operações sem
ganho estrutural.

Exemplo:

```text
banco:    ix_adaptive_audit_org
metadata: ix_adaptive_audit_events_organization_id
tabela/coluna: adaptive_audit_events.organization_id
```

Distribuição principal dos 181 pares:

- aprendizagem adaptativa: 43;
- infraestrutura e operações: 88;
- governança institucional: 33;
- intervenções: 15;
- pré-requisitos de habilidades: 2.

Diagnóstico: drift de nomenclatura causado principalmente por `index=True`,
que produz nomes automáticos diferentes dos nomes explícitos usados nas
migrations. A correção preferida é declarar no metadata os nomes canônicos já
instalados. Renomear fisicamente centenas de índices sem necessidade aumenta
lock, tempo de implantação e risco de rollback.

## 3. Índices esperados pelo metadata e ausentes no banco

Depois de retirar os 181 pares de renome e uma troca de constraint por índice,
restam 74 especificações de índice presentes apenas no metadata, em 39 tabelas:

- aprendizagem adaptativa e acessibilidade: 44;
- infraestrutura e operações: 19;
- laboratório estatístico: 9;
- autenticação (`auth_sessions.family_id`): 1;
- Analytics/intervenção (`learning_intervention_events.organization_id`): 1.

Os maiores grupos são:

- `adaptive_learning_paths`: 6;
- `adaptive_feedbacks`, `adaptive_recommendations`, `adaptive_skill_states`,
  `hint_usages` e `spaced_review_schedules`: 4 cada;
- `spaced_review_events` e `student_difficulty_profiles`: 3 cada;
- `adaptive_review_schedules`, `deployment_approvals`, `failover_events`,
  `operational_metric_snapshots`, `progression_decisions`,
  `restore_entity_jobs`, `skill_prerequisites`, `statistical_reports` e
  `worker_drain_events`: 2 cada;
- as demais tabelas: 1 cada.

Esses itens são candidatos, não autorização para criar todos os índices. Cada
um precisa ser confrontado com a migration de origem, cardinalidade, consultas
reais, índices compostos existentes e custo de escrita.

## 4. Índices existentes que o metadata tentaria remover

Há 13 índices físicos, agrupados em 12 especificações básicas, que existem no
banco e não estão representados no metadata:

- `ix_adaptive_skill_dimension`;
- `ix_assignment_item_metrics_assignment_question_id`;
- `ix_document_chunks_embedding_hnsw`;
- `ix_document_chunks_search_vector`;
- `uq_hq_editor_single_back_cover`;
- `uq_hq_editor_single_cover`;
- `ix_hq_editor_page_type`;
- `ix_material_assignments_status_due`;
- `ix_alert_events_org_status`;
- `ix_metric_snapshots_name_time`;
- `ix_skill_prereq_dimension`;
- `ix_student_attempts_student_status`;
- `ix_user_notifications_user_status`.

Os dois índices `uq_hq_editor_single_*` compartilham colunas, mas possuem
predicados parciais diferentes para capa e contracapa; por isso são dois
objetos físicos em uma única especificação básica.

Risco: a remoção automática degradaria busca vetorial/textual, consultas
operacionais e de entrega, além de eliminar a garantia de capa/contracapa única
por projeto. Os índices especializados devem ser descritos no metadata ou
explicitamente protegidos pela política de autogeração.

## 5. Constraints de unicidade

O Alembic propõe remover estas 10 constraints:

- `art_direction_presets_code_key`;
- `assignment_item_metrics_assignment_question_id_key`;
- `auth_sessions_legacy_refresh_token_hash_key`;
- `auth_sessions_previous_refresh_token_hash_key`;
- `auth_sessions_refresh_token_hash_key`;
- `computational_thinking_pillars_code_key`;
- `creative_bibles_generation_project_id_key`;
- `uq_organizations_slug`;
- `password_reset_tokens_token_hash_key`;
- `uq_users_email`.

Somente `assignment_item_metrics.assignment_question_id` aparece também como
um índice único esperado pelo metadata. Nos outros nove casos, o metadata não
oferece substituto equivalente.

Risco crítico: aceitar o diff removeria garantias de identidade e segurança,
incluindo unicidade de usuário, organização, tokens de sessão e tokens de
recuperação de senha. A ação correta é restaurar essas constraints nos modelos,
preservando os nomes existentes.

## 6. Nullability de `material_assignments.package_id`

Estado encontrado:

```text
migration 0014 / banco: package_id NOT NULL
modelo atual:             package_id nullable
migration 0054:           adiciona assessment_version_id, mas não altera package_id
```

O modelo sugere que uma entrega pode ter `assessment_version_id` sem
`package_id`, mas o banco ainda bloqueia essa gravação. Antes de alterar a
coluna é necessário confirmar a invariável canônica:

- ao menos uma origem deve existir;
- definir se ambas podem coexistir;
- validar e corrigir registros legados;
- criar, se aplicável, uma `CHECK constraint` que expresse a regra.

Esse é o único drift que provavelmente exige alteração real de coluna. Ele não
deve ser incluído em uma migration ampla com centenas de mudanças não
relacionadas.

## Riscos

### Críticos

- migration autogerada sem revisão remove constraints de unicidade de
  autenticação e identidade;
- remoção dos índices HNSW, de busca textual e parciais da HQ;
- conversão indiscriminada de 85 colunas `JSONB` para `JSON`.

### Altos

- divergência de nullability pode impedir entregas baseadas apenas em versão de
  avaliação;
- 74 índices candidatos podem representar lacunas reais de desempenho, mas
  também podem ser redundantes com índices compostos;
- renomear 181 índices pode provocar locks e churn operacional sem benefício.

### Médios

- ausência de uma convenção explícita de nomes no `Base`;
- uso combinado de `index=True`, nomes explícitos em migrations e índices
  PostgreSQL especializados;
- `alembic check` não pode ser usado como gate de CI enquanto o metadata não
  representar o schema canônico.

## Estratégia recomendada

1. Corrigir somente o metadata, sem migration:
   - representar como `JSONB` as 85 colunas já instaladas como JSONB;
   - declarar as 10 constraints de unicidade com seus nomes atuais;
   - declarar os 181 índices com os nomes já existentes;
   - representar e preservar índices compostos, parciais, GIN e HNSW.
2. Executar novamente `alembic check`. O alvo desta fase é eliminar operações
   destrutivas e renomes artificiais.
3. Revisar os 74 índices candidatos por domínio e por plano de consulta.
4. Definir a invariável de origem de `material_assignments` e testar dados
   existentes.
5. Somente então propor uma migration curta baseada em
   `0054_delivery_model_sync`, contendo exclusivamente:
   - a mudança de nullability/constraint aprovada;
   - os índices realmente necessários e não redundantes.
6. Validar a migration em cópia do banco:
   - upgrade;
   - downgrade;
   - novo upgrade;
   - `alembic current`, `heads` e `check`;
   - testes de autenticação, isolamento organizacional, entrega, RAG e HQ;
   - análise de locks e tempo de criação dos índices.

## Comandos de evidência

```powershell
docker-compose exec -T backend alembic current
docker-compose exec -T backend alembic heads
docker-compose exec -T backend alembic check
```

A classificação detalhada foi feita com `MigrationContext` e
`produce_migrations` dentro do container backend. A conexão terminou em
`ROLLBACK`.

## Atualização — alinhamento do metadata

Na branch `chore/alembic-metadata-alignment`, o metadata foi alinhado sem criar
ou aplicar migration:

- as 85 colunas foram declaradas como `JSONB`, mantendo quatro colunas de HQ
  que são `JSON` de fato;
- as 10 constraints de unicidade instaladas foram registradas explicitamente;
- os 13 índices compostos, parciais, GIN e HNSW existentes foram registrados;
- pares de índice com mesma tabela, colunas, ordem, unicidade e opções de
  dialeto, mas nomes diferentes, passaram a ser normalizados durante a
  autogeração.

A normalização de nomes é conservadora: somente remove do script o par
`drop/create` semanticamente idêntico. Adições isoladas e alterações de coluna,
ordem, unicidade ou opções PostgreSQL continuam visíveis.

Resultado após o alinhamento:

| Operação | Antes | Depois |
| --- | ---: | ---: |
| `modify_type` | 85 | 0 |
| `remove_constraint` | 10 | 0 |
| `remove_index` | 194 | 0 |
| `add_index` | 256 | 74 |
| `modify_nullable` | 1 | 1 |
| total | 546 | 75 |

O `alembic check` continua falhando intencionalmente enquanto os 74 índices
candidatos e a nullability de `material_assignments.package_id` não forem
decididos. Nenhuma dessas 75 operações foi ocultada ou aplicada.
