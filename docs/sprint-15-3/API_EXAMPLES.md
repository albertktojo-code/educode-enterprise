# Exemplos de API - Sprint 15.3

## Template estrutural

`GET /api/v1/instrument-governance/templates/roman-gonzalez`

## Licenca

`POST /api/v1/instrument-governance/licenses`

```json
{
  "instrument_id": "00000000-0000-0000-0000-000000000000",
  "license_holder": "Instituicao autorizada",
  "permission_reference": "Processo interno 2026/001",
  "rights_scope": {"actions": ["IMPORT", "ADMINISTER", "SCORE"]},
  "permitted_territories": ["BR"]
}
```

## Simulacao

`POST /api/v1/instrument-governance/score-simulations`

```json
{
  "instrument_id": "00000000-0000-0000-0000-000000000000",
  "raw_scores": {"TOTAL": 18},
  "profile": {"locale": "pt-BR", "age": 12, "school_year": 7}
}
```
