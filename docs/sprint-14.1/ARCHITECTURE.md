# Arquitetura — Sprint 14.1

## Fluxo unificado

```text
atividade existente
  → tentativa e resposta existentes
  → evidência da Sprint 14
  → adaptação da Sprint 14.1
  → pista, feedback, revisão, dificuldade ou progressão
  → auditoria e histórico
```

A Sprint 14.1 não substitui o modelo de avaliações. Os identificadores `attempt_id`, `response_id`, `student_id`, `learning_node_id`, `resource_type` e `resource_id` conectam a adaptação à trilha pedagógica existente.

## Serviços determinísticos

- `hints.py`: seleciona a menor pista elegível ainda não utilizada;
- `spaced_review.py`: calcula intervalo com resultado, domínio, confiança, pistas e atraso;
- `feedback.py`: seleciona feedback por erro e nível de domínio;
- `difficulty.py`: calcula dificuldade individual e dificuldade observada;
- `progression.py`: avalia condições JSON versionadas;
- `accessibility.py`: gera transformação acessível sem sobrescrever o original.

## Persistência

A migration cria nove conjuntos de registros:

1. `graduated_hints`;
2. `hint_usages`;
3. `spaced_review_schedules`;
4. `spaced_review_events`;
5. `adaptive_feedbacks`;
6. `student_difficulty_profiles`;
7. `resource_difficulty_metrics`;
8. `progression_rules` e `progression_decisions`;
9. `accessible_resource_versions`.

## Explicabilidade

Todos os cálculos retornam motivo, versão da regra, fatores utilizados e indicador de revisão humana.

## Compatibilidade

`compat.py` procura as dependências de banco usadas nas estruturas mais comuns das sprints anteriores. A integração nunca cria silenciosamente outro banco ou outra sessão.
