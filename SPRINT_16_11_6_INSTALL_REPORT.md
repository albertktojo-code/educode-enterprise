# Relatório de instalação — Sprint 16.11.6

## Resultado

- Sprint: `16.11.6 — Monitoramento docente em tempo real`
- Versão instalada: `0.16.11.6`
- Build ID: `sprint-16.11.6-hq-teacher-monitoring`
- Data da validação: `2026-07-30`
- Resultado: `sucesso com riscos residuais documentados`
- Migration nova: `não`
- Alembic current: `0055_delivery_source_invariant (head)`
- Alembic heads: `0055_delivery_source_invariant (head)`
- Quantidade de heads: `1`

## Arquitetura instalada

A sprint reutiliza os domínios canônicos:

- Assessment Delivery para publicação, audiência, sessões, eventos, tentativas,
  pausa, retomada e tempo adicional;
- estado da experiência pós-HQ para posição e progresso;
- feedback aprovado para dicas graduadas;
- notificações de usuário para comunicação persistente;
- auditoria institucional para ações docentes.

Não foram criados modelos, tabelas, sessões, tentativas, respostas ou sistema de
mensageria paralelos. O painel usa polling autenticado a cada cinco segundos.

## Validações executadas

### Backend

- suíte completa: `508 passed, 3 skipped, 1 warning`;
- tempo da suíte final: `10.78s`;
- sintaxe Python e regras Ruff fatais: aprovadas;
- Ruff focado nos arquivos da sprint: aprovado;
- teste de integração com PostgreSQL real: aprovado com rollback;
- isolamento organizacional, privacidade e políticas docentes: aprovados;
- rotas confirmadas no OpenAPI:
  - `/api/v1/comic-page-editor/activity-deliveries/{delivery_id}/monitoring`;
  - `/api/v1/assessment-delivery/sessions/{session_id}/actions`.

O único warning da suíte é a depreciação do adaptador `httpx` usado pelo
`starlette.testclient`.

### Frontend

- `npm run lint`: aprovado;
- `npm run build`: aprovado;
- TypeScript: aprovado;
- Vite: `223 modules transformed`;
- bundle principal: `901.51 kB`, gzip `226.58 kB`;
- endpoint do frontend: HTTP `200`.

### Smoke E2E

- script: `scripts/e2e-sprint-16-11-6.ps1`;
- frontend: HTTP `200` e título do EduCode confirmado;
- liveness/readiness/versão: aprovados;
- contratos OpenAPI da sprint: aprovados;
- acesso anônimo ao monitoramento: bloqueado;
- smoke visual desktop e móvel: aprovado sem erros de console;
- fluxo autenticado no navegador: não executado, pois a credencial de bootstrap
  documentada não corresponde mais ao usuário instalado;
- nenhuma senha foi redefinida e nenhum usuário de teste foi criado.

### Banco e Alembic

- `alembic upgrade head`: aprovado;
- `alembic current`: `0055_delivery_source_invariant (head)`;
- `alembic heads`: `0055_delivery_source_invariant (head)`;
- downgrade específico: não aplicável, pois a sprint não possui migration;
- `alembic check`: sem diferenças de tabela, coluna, tipo ou nulabilidade.

O check continua retornando código não zero por 74 candidatos únicos de índice
históricos já documentados. Nenhum deles foi convertido em migration funcional
nesta sprint.

### Docker e saúde

- `docker-compose config --quiet`: aprovado;
- imagem do backend: construída;
- imagem do frontend: construída;
- backend: `healthy`;
- PostgreSQL: `healthy`;
- Redis: `healthy`;
- health live: `alive`;
- health ready: `ready`;
- health do editor de HQ: sprint `16.11.6`;
- health do Assessment Delivery: sprint `16.11.6`.

## Verificações de segurança

- organização derivada do contexto autenticado;
- monitor restrito a papéis docentes/editoriais existentes;
- nenhuma resposta do estudante é retornada no snapshot;
- gabarito permanece oculto até liberação permitida;
- eventos do estudante não podem simular origem docente;
- ações docentes sensíveis geram evento, notificação quando aplicável e
  auditoria;
- nenhuma decisão pedagógica é tomada automaticamente.

## Riscos residuais

1. O bundle principal do frontend permanece acima do limite recomendado de
   500 kB e deve receber code splitting em uma frente de performance.
2. O drift histórico de 74 índices continua registrado para tratamento
   separado.
3. O mypy focado atravessa dependências antigas e encontra 12 erros preexistentes
   em Assessment Hub, comic reader e adaptive evolution; nenhum erro foi
   reportado nos arquivos da Sprint 16.11.6.
4. Polling oferece atualização próxima do tempo real, com latência nominal de
   até cinco segundos.

## Rollback

Não há rollback de banco. Para reverter a sprint, restaurar os arquivos da
versão anterior e reconstruir backend e frontend. Eventos, notificações e
auditorias já persistidos devem ser mantidos como histórico institucional.
