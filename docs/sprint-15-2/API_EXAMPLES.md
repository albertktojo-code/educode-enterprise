# Exemplos de API - Sprint 15.2

## Criar publicacao

```json
{
  "code": "PC-6A-2026",
  "title": "Diagnostico de Pensamento Computacional",
  "source_type": "BLUEPRINT",
  "source_id": "00000000-0000-0000-0000-000000000001",
  "item_snapshot": [
    {"question_version_id": "00000000-0000-0000-0000-000000000002", "position": 0}
  ],
  "starts_at": "2026-08-01T08:00:00-03:00",
  "ends_at": "2026-08-05T18:00:00-03:00",
  "duration_minutes": 50,
  "max_attempts": 1,
  "navigation_mode": "LINEAR_WITH_REVIEW",
  "autosave_seconds": 15
}
```

## Autosave

```json
{
  "session_item_id": "00000000-0000-0000-0000-000000000003",
  "sequence_number": 4,
  "response": {"selected": ["B"]},
  "client_timestamp": "2026-08-01T09:12:00-03:00"
}
```
