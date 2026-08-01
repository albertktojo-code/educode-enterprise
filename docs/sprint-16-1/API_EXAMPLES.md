# Exemplos de API - Sprint 16.1

## Validar grid

```http
POST /api/v1/comic-page-editor/layouts/validate
```

```json
{
  "code": "GRID_CUSTOM_01",
  "name": "Destaque e apoio",
  "grid_definition": {
    "gutter": 0.02,
    "page_margin": 0.02,
    "panels": [
      {"x": 0, "y": 0, "width": 0.66, "height": 0.5, "shape": "RECTANGLE"},
      {"x": 0.67, "y": 0, "width": 0.33, "height": 0.5, "shape": "RECTANGLE"}
    ]
  }
}
```

## Criar pagina

```http
POST /api/v1/comic-page-editor/projects/{project_id}/pages
```

## Criar job de geracao

```http
POST /api/v1/comic-page-editor/projects/{project_id}/generation-jobs
```

```json
{
  "continue_in_background": true,
  "generate_images": true,
  "validate_bncc": true,
  "validate_accessibility": true
}
```

## Autosave

O checksum deve ser SHA-256 do JSON canonico do payload.

```http
POST /api/v1/comic-page-editor/projects/{project_id}/autosave
```
