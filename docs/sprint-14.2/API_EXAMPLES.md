# Exemplos de API — Sprint 14.2

## Recomendação por histórico

```json
{
  "student_id": "11111111-1111-1111-1111-111111111111",
  "learning_node_id": "22222222-2222-2222-2222-222222222222",
  "current_mastery": 0.48,
  "current_confidence": 0.68,
  "candidate_interventions": ["REVISAO_GUIADA", "ATIVIDADE_VISUAL"],
  "history": [
    {
      "intervention_type": "REVISAO_GUIADA",
      "mastery_before": 0.31,
      "mastery_after": 0.47,
      "completion_rate": 1,
      "hint_level_average": 1.5,
      "attempts_average": 1.8,
      "days_ago": 5
    }
  ]
}
```

## Modelo adaptativo

```json
{
  "name": "Progressão institucional",
  "version": "1.0.0",
  "description": "Modelo determinístico para simulação institucional.",
  "scope_type": "ORGANIZATION",
  "algorithm_type": "DETERMINISTIC_RULES",
  "configuration": {
    "advance_mastery": 0.75,
    "minimum_confidence": 0.55,
    "minimum_evidences": 3,
    "reinforce_below": 0.40
  },
  "input_schema": {},
  "output_schema": {},
  "status": "DRAFT"
}
```

## Experimento controlado

```json
{
  "name": "Comparação de feedback",
  "description": "Comparar feedback breve e feedback orientado.",
  "hypothesis": "O feedback orientado aumenta o ganho médio.",
  "primary_metric": "mastery_gain",
  "metric_direction": "HIGHER_IS_BETTER",
  "assignment_strategy": "DETERMINISTIC_HASH",
  "minimum_sample_per_strategy": 20,
  "strategies": [
    {"key": "A", "name": "Feedback breve", "configuration": {}},
    {"key": "B", "name": "Feedback orientado", "configuration": {}}
  ]
}
```
