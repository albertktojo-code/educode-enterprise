# Exemplos de API — Sprint 15.4

Prefixo: `/api/v1/assessment-review`

## Criar rubrica

```json
{
  "code": "RUB-DISC-01",
  "name": "Resposta discursiva",
  "description": "Rubrica para explicação de estratégias.",
  "scope_type": "QUESTION"
}
```

## Criar versão

```json
{
  "maximum_score": 10,
  "criteria": [
    {"code": "CONCEITO", "name": "Domínio conceitual", "maximum_score": 6},
    {"code": "ESTRATEGIA", "name": "Estratégia", "maximum_score": 4}
  ],
  "score_rules": {"rounding": 2}
}
```

## Registrar pontuação

```json
{
  "scores": [
    {
      "criterion_code": "CONCEITO",
      "criterion_name": "Domínio conceitual",
      "awarded_score": 5,
      "maximum_score": 6,
      "skill_scores": {"EF06MA07": {"name": "Frações", "weight": 1}}
    }
  ],
  "finalize": true,
  "completion_comment": "Revisão docente concluída."
}
```
