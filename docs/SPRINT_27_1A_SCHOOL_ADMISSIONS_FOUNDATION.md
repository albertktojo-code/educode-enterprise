# Sprint 27.1A — Fundação da Secretaria Digital e Matrículas

## Objetivo

Esta entrega inaugura o domínio administrativo escolar do EduCode Admin sem
duplicar autenticação, organizações, turmas, participantes, notificações ou
auditoria. O incremento cobre unidades escolares, perfis mínimos de estudantes
e responsáveis, inscrições, capacidade, reserva de vaga, lista de espera e
aprovação de matrícula.

## Incremento entregue

- cadastro de unidades escolares por organização;
- vínculo opcional de turma com unidade e turno;
- atribuições administrativas institucionais por unidade, preservando o RBAC
  canônico de `memberships`;
- perfis de estudante e responsável, com vínculos e papéis familiares;
- inscrição administrativa com estudante e responsáveis;
- capacidade máxima por turma e reserva temporária de vaga;
- lista de espera ordenada quando a turma está lotada;
- aprovação idempotente da inscrição;
- criação de `classroom_enrollments` somente quando o estudante já possui uma
  identidade de usuário válida; caso contrário, a matrícula fica em
  `pending_identity`;
- painel administrativo em `/secretaria` com unidades, turmas, capacidade,
  inscrições e ações operacionais;
- eventos de auditoria e notificações canônicas;
- sete feature flags institucionais, inicialmente desativadas.

## Limites e decisões de segurança

- CPF, RG e imagens de documentos não fazem parte desta fundação. Esses dados
  serão introduzidos somente com criptografia, versionamento documental,
  retenção e política explícita de acesso na Sprint 27.1B.
- O cliente nunca define `organization_id`; o escopo vem da sessão autenticada.
- Consultas e escritas do domínio usam organização, papel e, quando aplicável,
  unidade escolar.
- `owner` e `admin` podem preparar a instituição mesmo com a flag desativada.
  Demais atribuições administrativas dependem de `SCHOOL_ADMISSIONS_ENABLED`.
- O financeiro escolar futuro permanece separado do faturamento da plataforma.
  Nenhuma tabela financeira foi criada nesta sprint.

## Banco de dados

A migration `0059_school_admissions` sucede `0058_student_certificates` e cria:

- `school_units`;
- `institutional_staff_assignments`;
- `student_profiles`;
- `guardian_profiles`;
- `student_guardian_links`;
- `student_enrollment_applications`;
- `student_enrollments`;
- `class_capacity`;
- `seat_reservations`;
- `enrollment_waitlists`.

Também adiciona `school_unit_id` e `shift` a `classrooms`. A decisão da última
vaga é serializada pelo bloqueio da configuração de capacidade; reservas
expiradas deixam de contar imediatamente e são consolidadas durante operações
transacionais de reserva ou aprovação.

## API e interface

O router `/api/v1/school-admissions` oferece unidades, capacidade, inscrições,
reserva/lista de espera, aprovação e dashboard. A página `/secretaria` usa o
cliente HTTP autenticado central e contém estados de carregamento, aviso e vazio,
labels, foco visível, `aria-live` e layout responsivo.

## Feature flags

- `SCHOOL_ADMISSIONS_ENABLED`
- `SCHOOL_SECRETARIAT_ENABLED`
- `SCHOOL_REPORT_CARDS_ENABLED`
- `SCHOOL_EVENTS_ENABLED`
- `SCHOOL_ANNOUNCEMENTS_ENABLED`
- `SCHOOL_FINANCE_ENABLED`
- `FAMILY_PORTAL_ENABLED`

Todas são semeadas como `false` para cada organização.

## Instalação

Execute na raiz consolidada:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-sprint-27-1a.ps1
```

O instalador valida o manifesto e o estado-base, preserva arquivos não
rastreados, cria backup, executa testes e builds antes da migration, aplica a
migration, recria os serviços, verifica o healthcheck e grava um relatório em
`storage/sprint-reports/`.

## Rollback

O rollback destrutivo não é automático. Antes de qualquer reversão:

1. coloque a aplicação em manutenção e crie um novo backup;
2. confirme que não existem matrículas, inscrições, reservas ou perfis que
   precisem ser preservados;
3. prefira restaurar o backup integral criado antes da instalação;
4. se não houver dados do novo domínio, execute
   `docker compose run --rm backend alembic downgrade 0058_student_certificates`;
5. restaure a revisão anterior do código e reconstrua backend e frontend;
6. execute `docker compose up -d` e valide `/api/v1/health/ready`.

A migration remove as tabelas em ordem inversa e restaura `classrooms`, mas o
downgrade apaga todos os dados administrativos criados pela sprint.

## Validações executadas

- lint e formatação Python;
- testes focados e contratos estáticos;
- teste integrado em PostgreSQL descartável;
- isolamento por organização, RBAC, auditoria e idempotência;
- upgrade, downgrade para `0058` e novo upgrade em banco descartável;
- lint e build do frontend;
- build de backend e frontend;
- healthcheck dos serviços;
- inspeção visual da página `/secretaria`.

O comando `alembic check` ainda sinaliza divergências históricas de índices e
constraints anteriores a esta sprint. A saída foi conferida separadamente e não
contém tabelas nem colunas do domínio `school_admissions`; a correção global
desse legado permanece fora do escopo incremental desta entrega.

## Critérios de aceitação

- [x] uma organização não acessa dados de outra;
- [x] unidade, turno e capacidade podem ser configurados;
- [x] reserva repetida não consome duas vagas;
- [x] aprovação repetida retorna a matrícula existente;
- [x] turma lotada direciona a próxima inscrição à lista de espera;
- [x] estudante sem usuário fica em `pending_identity` sem participante falso;
- [x] ações relevantes geram auditoria e notificação;
- [x] a interface está conectada à API real e possui estados acessíveis;
- [x] testes foram executados antes da aplicação da migration principal;
- [x] backup, rollback, manifesto e SHA-256 estão documentados.

## Próximo incremento

A Sprint 27.1B deve implementar documentos de matrícula com armazenamento
seguro, versionamento, política de retenção, criptografia de campos sensíveis e
fluxo de revisão administrativa.
