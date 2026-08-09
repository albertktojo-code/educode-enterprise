# Sprint 18.11 — Certificados verificáveis

Fundação do EduCode Credentials para emissão docente baseada em evidências curadas,
listagem privada do estudante e revogação auditada. Cada certificado recebe código
único e referencia as entradas do portfólio sem copiar atividades ou resultados.

A migration `0058_student_certificates`, baseada em `0057_student_portfolio`, cria uma
tabela com emissor, estudante, evidências, estado e dados de revogação. O rollback remove
somente certificados. Verificação pública e exportação visual ficam para incremento posterior.
