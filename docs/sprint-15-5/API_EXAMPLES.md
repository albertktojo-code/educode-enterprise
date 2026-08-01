# Exemplos de API - Sprint 15.5

## Simular análise de item

```http
POST /api/v1/assessment-analytics/simulate/item
```

```json
{
  "predicted_difficulty": 0.55,
  "item_scores": [1, 1, 0, 1, 0, 1],
  "total_scores": [90, 82, 45, 76, 42, 71],
  "omitted": 0,
  "upper_correct": 3,
  "upper_total": 3,
  "lower_correct": 1,
  "lower_total": 3,
  "minimum_sample": 5
}
```

## Simular distratores

```http
POST /api/v1/assessment-analytics/simulate/distractors
```

```json
{
  "selections": ["A", "A", "B", "C", "A"],
  "correct_option": "A",
  "minimum_functioning_rate": 0.05
}
```

## Verificar privacidade

```http
POST /api/v1/assessment-analytics/privacy/check
```

```json
{
  "sample_size": 4,
  "minimum_group_size": 5
}
```
