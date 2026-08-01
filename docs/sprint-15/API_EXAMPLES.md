# Exemplos de API — Sprint 15

## Criar questao

```http
POST /api/v1/assessment-hub/questions
```

```json
{
  "code": "MAT-EF06-0001",
  "title": "Equivalencia de fracoes",
  "subject": "Matematica",
  "school_year": "6 ano"
}
```

## Criar versao

```http
POST /api/v1/assessment-hub/questions/{question_id}/versions
```

```json
{
  "question_type": "SINGLE_CHOICE",
  "statement": "Qual fracao e equivalente a 1/2?",
  "options": [
    {"id": "A", "text": "2/4"},
    {"id": "B", "text": "2/5"}
  ],
  "correct_answer": {"value": "A"},
  "predicted_difficulty": 0.35,
  "max_score": 1
}
```

## Cadastrar instrumento externo

O cadastro armazena metadados e regras autorizadas. Itens de terceiros devem ser importados apenas quando houver permissao.

```json
{
  "code": "PC-EXTERNO-01",
  "name": "Instrumento externo de Pensamento Computacional",
  "version": "autorizada",
  "instrument_type": "COMPUTATIONAL_THINKING",
  "description": "Cadastro estrutural sem itens protegidos.",
  "license_status": "REQUIRES_PERMISSION"
}
```
