# Changelog

## Sprint 27.2B — 2026-08-09

### Adicionado

- solicitações tenant-scoped de rematrícula e transferência interna ou externa;
- aprovação de rematrícula e transferência interna reutilizando matrícula, turma e vagas;
- preservação do vínculo anterior como histórico em transferências;
- módulo visual separado `/secretaria/movimentacoes`, migration reversível
  `0062_enrollment_movements`, testes, instalador e manifesto.

### Segurança

- criação e análise restritas à equipe autorizada da Secretaria;
- decisões e solicitações registradas na auditoria operacional;
- migration aplicada somente depois de testes e validação em banco descartável.

## Sprint 27.2A — 2026-08-09

### Adicionado

- templates institucionais de contrato com variáveis controladas;
- geração e regeneração em versões imutáveis com conteúdo e SHA-256;
- aceite idempotente restrito ao responsável autenticado e vinculado ao estudante;
- cancelamento administrativo de contratos ainda não aceitos;
- módulo visual `/secretaria/contratos`, migration `0061_enrollment_contracts`, testes,
  instalador, rollback e manifesto.

### Segurança

- contratos aceitos não podem ser regenerados nem cancelados diretamente;
- aceite registra versão, responsável, usuário, timestamp, IP e hash sem expor dados civis;
- integrações externas de assinatura e financeiro permanecem fora deste incremento.

## Sprint 27.1B — 2026-08-09

### Adicionado

- checklist institucional de documentos de matrícula por organização e unidade;
- upload privado de PDF, JPEG e PNG com validação de assinatura, tamanho e SHA-256;
- histórico imutável de versões, revisão administrativa e download autenticado;
- migration reversível `0060_enrollment_documents` e teste integrado em PostgreSQL;
- manifesto, instalador seguro, relatório e documentação operacional da sprint.

### Alterado

- Secretaria Digital separada visualmente em painel, matrículas, documentos e turmas/vagas;
- smoke test atualizado para o head `0060_enrollment_documents`.

### Segurança

- chaves de armazenamento nunca são expostas pela API e downloads usam `no-store`;
- envio pelo responsável permanece adiado para o Portal da Família; nesta sprint o acesso é
  restrito à equipe institucional autorizada.

## Sprint 27.1A — 2026-08-09

### Adicionado

- fundação multi-organização da Secretaria Digital e Matrículas;
- unidades escolares, atribuições administrativas e perfis familiares;
- capacidade, reserva de vaga, lista de espera e aprovação idempotente;
- página administrativa `/secretaria` e feature flags institucionais;
- migration reversível `0059_school_admissions`;
- testes de contrato, integração, instalador, manifesto e documentação.

### Alterado

- turmas agora podem pertencer a uma unidade escolar e possuir turno;
- navegação administrativa inclui a Secretaria Digital.

### Segurança

- documentos e identificadores civis sensíveis foram adiados para a Sprint
  27.1B, quando terão criptografia, retenção e controle de acesso próprios.
