# Exemplos de API

## Calcular revisão espaçada

```http
POST /api/v1/adaptive-evolution/reviews/calculate-next
Content-Type: application/json
```

```json
{
  "mastery_score": 0.68,
  "confidence_score": 0.72,
  "result_score": 0.80,
  "hint_level_used": 1,
  "previous_interval_days": 7
}
```

## Calcular dificuldade observada

```json
{
  "predicted_difficulty": 0.45,
  "attempts_count": 80,
  "correct_count": 42,
  "average_attempts": 1.9,
  "average_hint_level": 1.6,
  "abandonment_rate": 0.08,
  "average_time_seconds": 170,
  "expected_time_seconds": 120
}
```

## Criar regra de avanço

```json
{
  "name": "Avanço padrão em Matemática",
  "version": "1.0.0",
  "description": "Avança quando há evidência suficiente e pré-requisitos concluídos.",
  "scope_type": "SUBJECT",
  "conditions": {
    "minimum_mastery_score": 0.7,
    "minimum_confidence": 0.6,
    "minimum_evidences": 3,
    "required_prerequisites": true,
    "maximum_high_level_hints": 1
  },
  "result_action": "ADVANCE",
  "priority": 100,
  "requires_teacher_approval": false
}
```

## Gerar versão em linguagem simples

```json
{
  "source_resource_type": "ACTIVITY",
  "source_resource_id": "00000000-0000-0000-0000-000000000001",
  "title": "Atividade sobre frações",
  "content": "Identifique as informações e posteriormente efetue o cálculo solicitado.",
  "adaptation_type": "PLAIN_LANGUAGE",
  "learning_objective": "Resolver problemas com frações.",
  "expected_answer": "Definida no recurso original.",
  "assessment_criteria": ["Representação", "Justificativa"]
}
```
