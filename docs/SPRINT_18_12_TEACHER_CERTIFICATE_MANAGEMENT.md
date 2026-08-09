# Sprint 18.12 — Gestão de certificados pelo professor

## Incremento entregue

- Nova área `EduCode Credentials` em `/credentials/certificados` para professores e gestores.
- Seleção de estudantes ativos da organização.
- Consulta das evidências curadas pelo estudante, com reflexão e resultado preservados.
- Emissão de certificado a partir de uma ou mais evidências.
- Histórico com código verificável, estado ativo/revogado e motivo da revogação.
- Revogação pela mesma área, mantendo trilha de auditoria já existente.

## Segurança e persistência

As consultas de gestão exigem papel de educador e filtram estudantes, evidências e certificados pela organização do ator. A sprint reutiliza as tabelas e os eventos de auditoria da Sprint 18.11; portanto, não cria nem aplica migration.

## Próximo incremento

A Sprint 18.13 poderá disponibilizar verificação pública por código e exportação visual em PDF/QR Code.
