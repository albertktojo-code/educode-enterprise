# Exemplos de API - Sprint 16.2

Prefixo: `/api/v1/comic-layout-studio`

## Criar documento de canvas

```json
POST /documents
{
  "comic_project_id": "UUID",
  "page_id": "UUID",
  "name": "Pagina 3 - desafio",
  "page_width": 210,
  "page_height": 297,
  "dpi": 300,
  "bleed_mm": 3,
  "safe_margin_mm": 8,
  "grid_size": 5,
  "snap_enabled": true
}
```

## Criar camada

```json
POST /documents/{document_id}/layers
{
  "layer_type": "SPEECH_BALLOON",
  "name": "Fala da Luna",
  "transform": {
    "x": 92,
    "y": 28,
    "width": 70,
    "height": 38,
    "rotation_deg": 0,
    "opacity": 1
  },
  "shape": "ELLIPSE",
  "style": {"font_size": 14},
  "content": {"text": "Vamos decompor o problema!"}
}
```

## Executar pre-flight

```json
POST /documents/{document_id}/preflight
{
  "output_format": "PDF",
  "minimum_dpi": 150,
  "persist_findings": true
}
```

## Solicitar exportacao

```json
POST /documents/{document_id}/export-jobs
{
  "preset_id": "UUID",
  "output_format": "PDF",
  "run_preflight": true,
  "allow_warnings": true
}
```
