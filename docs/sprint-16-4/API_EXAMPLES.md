# Exemplos de API

## Criar sessão de revisão

```http
POST /api/v1/comic-review-publish/review-sessions
```

```json
{
  "comic_project_id": "00000000-0000-0000-0000-000000000001",
  "comic_version_id": "00000000-0000-0000-0000-000000000002",
  "title": "Revisão final da HQ Frações em Ação",
  "description": "Revisão pedagógica, visual e de acessibilidade."
}
```

## Criar comentário em um quadro

```http
POST /api/v1/comic-review-publish/review-sessions/{session_id}/threads
```

```json
{
  "anchor_type": "PANEL",
  "panel_id": "00000000-0000-0000-0000-000000000003",
  "title": "Contraste do balão",
  "body": "Aumentar o contraste entre o texto e o fundo.",
  "severity": "WARNING"
}
```

## Registrar decisão

```http
POST /api/v1/comic-review-publish/workflows/{workflow_id}/decisions
```

```json
{
  "decision": "APPROVE",
  "reviewer_role": "ACCESSIBILITY_REVIEWER",
  "note": "A versão atende aos critérios de acessibilidade."
}
```
