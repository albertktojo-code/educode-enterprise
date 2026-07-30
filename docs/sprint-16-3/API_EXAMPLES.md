# Exemplos da API — Sprint 16.3

Prefixo: `/api/v1/comic-visual-library`

## Criar biblioteca

```json
{
  "code": "hq-fracoes",
  "name": "Biblioteca da HQ de Frações",
  "scope": "COMIC",
  "comic_project_id": "00000000-0000-0000-0000-000000000001"
}
```

## Criar personagem

```json
{
  "library_id": "00000000-0000-0000-0000-000000000002",
  "name": "Luna",
  "slug": "luna",
  "identity_profile": {
    "hair": "cacheado preto",
    "eyes": "castanhos",
    "glasses": true,
    "age_group": "adulta"
  },
  "default_wardrobe": {"outfit": "uniforme azul"},
  "prompt_template": "Luna, professora, estilo de HQ educacional",
  "negative_prompt": "sem texto incorporado"
}
```

## Verificar consistência

```json
{
  "comic_project_id": "00000000-0000-0000-0000-000000000001",
  "page_id": "00000000-0000-0000-0000-000000000003",
  "panel_id": "00000000-0000-0000-0000-000000000004",
  "entity_type": "CHARACTER",
  "expected_snapshot": {"hair": "cacheado preto", "glasses": true},
  "observed_snapshot": {"hair": "cacheado preto", "glasses": false}
}
```

## Criar lote

```json
{
  "comic_project_id": "00000000-0000-0000-0000-000000000001",
  "name": "Gerar páginas 3 a 5",
  "default_locks": {"face": true, "hair": true, "wardrobe": true},
  "items": [
    {
      "page_id": "00000000-0000-0000-0000-000000000003",
      "panel_id": "00000000-0000-0000-0000-000000000004",
      "page_order": 3,
      "panel_order": 1
    }
  ]
}
```
