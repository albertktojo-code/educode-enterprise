# Sprint 10 — Learning Analytics

## Objetivo
Transformar tentativas, respostas e eventos de aprendizagem em indicadores pedagógicos claros, explicáveis e acionáveis.

## Entregas
- painel geral do professor;
- políticas de tentativa: primeira, última, melhor ou todas;
- evolução individual e coletiva;
- desempenho por habilidade BNCC e pilar de Pensamento Computacional;
- análise de questões, dificuldade, omissões, tempo e distratores;
- índice básico de discriminação;
- confiança da estimativa baseada na quantidade de evidências;
- alertas transparentes com regra e evidências;
- intervenções pedagógicas e acompanhamento;
- qualidade dos dados;
- progresso positivo do estudante;
- exportação CSV anonimizada;
- tarefas de atualização e snapshots históricos.

## Novas páginas
- `/analytics`
- `/analytics/turmas/{classroom_id}`
- `/analytics/estudantes/{student_id}`
- `/analytics/atividades/{assignment_id}`
- `/analytics/alertas`
- `/aluno/progresso`

## Migration
`0016_learning_analytics`

## Limite de escopo
Testes inferenciais como t de Student, ANOVA, Wilcoxon, tamanho do efeito e relatórios científicos ficam para a Sprint 11.
