# Changelog

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
