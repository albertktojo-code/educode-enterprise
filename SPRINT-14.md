# Sprint 14 — Aprendizagem Adaptativa e Trilhas Personalizadas

## Objetivo

Utilizar as evidências reais dos exercícios e avaliações dos estudantes para construir mapas de domínio, propor recomendações explicáveis e acompanhar trilhas personalizadas sob controle do professor.

## Fluxo ponta a ponta

```text
Avaliação ou exercício realizado
→ resposta e correção
→ evidência BNCC/PC
→ cálculo de domínio
→ confiança e tendência
→ recomendação explicável
→ revisão do professor
→ trilha aprovada
→ estudante realiza as etapas
→ revisão espaçada
→ novo cálculo de domínio
→ resultado descritivo da trilha
```

## Modelo explicável

A primeira versão é determinística e versionada. O cálculo utiliza:

- pontuação obtida e possível;
- peso da evidência;
- dificuldade registrada;
- recência;
- quantidade de evidências;
- consistência entre resultados;
- tendência entre evidências antigas e recentes.

Níveis:

- `not_assessed`;
- `insufficient_evidence`;
- `initial`;
- `developing`;
- `adequate`;
- `advanced`.

O domínio alto com poucas evidências não é apresentado como domínio consolidado.

## Recomendações

Tipos iniciais:

- diagnóstico;
- recuperação;
- reforço;
- consolidação;
- desafio avançado.

Toda recomendação registra:

- estudante ou grupo;
- habilidade ou pilar;
- domínio observado;
- confiança;
- quantidade de evidências;
- tendência;
- materiais propostos;
- versão do modelo;
- decisão do professor.

Nenhuma recomendação é enviada automaticamente ao estudante.

## Trilhas

Destinos possíveis:

- estudante;
- turma;
- grupo pedagógico temporário.

Cada trilha possui:

- objetivo;
- dimensão-alvo;
- meta de domínio;
- mínimo de evidências;
- etapas obrigatórias e opcionais;
- regras de avanço;
- revisões programadas;
- resultado antes/depois.

## Revisão espaçada

Agenda inicial:

```text
1 dia
7 dias
30 dias
```

Os intervalos são encurtados para domínio baixo e ampliados para domínio alto.

## Proteções pedagógicas

- sem ranking público;
- sem comparação nominal entre estudantes;
- sem rótulos permanentes;
- grupos invisíveis aos estudantes por padrão;
- recomendações com evidências insuficientes viram diagnóstico;
- IA não altera notas ou domínio calculado;
- professor aprova a trilha;
- resultados da trilha são descritivos, sem alegação causal automática.

## Integrações

### Núcleo de Avaliação Integrada

A fonte primária é `assessment_outcome_evidence`, mantendo vínculo com:

- avaliação e versão;
- publicação;
- tentativa;
- resposta;
- questão;
- estudante;
- habilidade ou pilar.

### Learning Analytics

O módulo adaptativo complementa, mas não substitui, os indicadores já calculados. Alertas e intervenções podem servir de contexto para novas trilhas.

### AI Fabric

A IA poderá futuramente sugerir materiais ou redigir explicações, mas o motor de domínio permanece determinístico. Toda geração continua submetida a revisão humana.

### Estatística

Os resultados antes/depois podem ser usados para criar datasets congelados e análises formais. O painel adaptativo não afirma causalidade.

## API

Prefixo:

```text
/api/v1/adaptive
```

Principais rotas:

- `GET /dashboard`;
- `POST /refresh`;
- `GET /students/{student_id}`;
- `POST /recommendations/generate`;
- `GET/PATCH /recommendations`;
- `POST /recommendations/{id}/create-path`;
- `GET/POST /paths`;
- `PATCH /paths/{id}/status`;
- `POST /steps/{id}/complete`;
- `GET/POST /groups`;
- `GET/POST /prerequisites`;
- `GET/POST /models`;
- `GET /me`.

## Migration

```text
0027_infra_continuity
        ↓
0028_adaptive_learning
```

Novas tabelas:

1. `adaptive_model_versions`;
2. `adaptive_learning_profiles`;
3. `adaptive_skill_states`;
4. `skill_prerequisites`;
5. `adaptive_student_groups`;
6. `adaptive_group_members`;
7. `adaptive_recommendations`;
8. `adaptive_recommendation_evidence`;
9. `adaptive_learning_paths`;
10. `adaptive_path_steps`;
11. `adaptive_review_schedules`;
12. `adaptive_path_outcomes`;
13. `adaptive_audit_events`.

## Critérios de conclusão

- domínio calculado a partir de evidências reais;
- confiança explícita;
- recomendação com justificativa;
- aprovação do professor;
- trilha disponível ao estudante;
- etapas progressivas;
- revisão espaçada;
- auditoria;
- isolamento por organização;
- ausência de ranking público.
