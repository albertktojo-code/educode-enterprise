# Segurança do EduCode

Não envie vulnerabilidades em issues públicas. Registre o incidente com a equipe responsável pela implantação, informando versão, ambiente, rota afetada, impacto e passos mínimos de reprodução, sem incluir dados de estudantes, tokens ou chaves.

## Controles da Sprint 13

- isolamento por organização no backend;
- headers de segurança e CSP;
- rate limiting com Redis e fallback local;
- request ID em todas as respostas;
- erros internos sem stack trace no frontend;
- auditoria encadeada por SHA-256;
- backups com checksum e restauração temporária real, restritos ao operador global;
- execução dos contêineres do backend como usuário não root;
- feature flags e modo de manutenção;
- políticas de retenção por organização.

Antes de produção, altere `JWT_SECRET_KEY`, senhas do PostgreSQL e todas as chaves de provedores.

Eventos globais de autenticação sem organização identificada são visíveis somente ao superusuário da plataforma.
