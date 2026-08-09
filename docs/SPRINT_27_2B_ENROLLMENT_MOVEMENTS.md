# Sprint 27.2B — Rematrículas e transferências

## Entrega

Este incremento amplia o domínio canônico `school_admissions` sem recriar estudantes,
matrículas, turmas ou vagas. A Secretaria passa a registrar e analisar rematrículas,
transferências internas e transferências externas em `/secretaria/movimentacoes`.

Uma rematrícula aprovada cria nova inscrição e novo vínculo para a turma/ano de destino. A
transferência interna faz o mesmo e encerra o vínculo de origem como `transferred`; a externa
encerra o vínculo e registra a instituição de destino. O histórico anterior é preservado.

## Segurança e consistência

- todas as consultas e tabelas são isoladas por organização;
- somente equipe autorizada da Secretaria cria ou analisa solicitações;
- aprovação interna reutiliza `approve_application`, inclusive controle transacional de vagas;
- solicitações duplicadas ou já analisadas são rejeitadas;
- criação e decisão geram eventos de auditoria, sem auditoria ampla adicional.

## Migration e instalação

A migration reversível `0062_enrollment_movements` depende de `0061_enrollment_contracts`.
Execute o instalador idempotente:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-sprint-27-2b.ps1
```

O instalador valida SHA-256, preserva arquivos não rastreados, cria backup e executa lint,
testes e build antes de aplicar a migration.

## Rollback

O downgrade remove somente as solicitações de movimentação. Antes dele, coloque o sistema em
manutenção, crie backup e exporte as solicitações que devam ser preservadas. Depois execute:

```powershell
docker compose run --rm backend alembic downgrade 0061_enrollment_contracts
```

Restaure o código anterior, reconstrua os serviços e valide o healthcheck. Para recuperar dados,
prefira restaurar o backup integral registrado no relatório de instalação.

## Validação

- lint Python, testes estáticos e build frontend antes da migration;
- integração PostgreSQL descartável com rematrícula e transferência externa;
- ciclo descartável `upgrade → downgrade → upgrade` aprovado;
- migration do banco principal somente após backup;
- arquivos não rastreados preservados.

## Limitações planejadas

Solicitação direta pelo responsável será conectada ao Portal da Família na Sprint 27.6. Emissão
de histórico escolar e integração entre instituições permanecem fora deste incremento.
