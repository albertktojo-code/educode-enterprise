# Relatorio de instalacao - Sprint 16.4

- Projeto: `C:\Users\lady_\Downloads\educode-enterprise-2.0-sprint-14\educode-enterprise-2.0-sprint-14`
- Compose: `C:\Users\lady_\Downloads\educode-enterprise-2.0-sprint-14\educode-enterprise-2.0-sprint-14\docker-compose.yml`
- Head anterior: `0038_comic_visual_library`
- Backup: `C:\Users\lady_\Downloads\educode-enterprise-2.0-sprint-14\educode-enterprise-2.0-sprint-14\.sprint-backups\sprint-16-4\20260728-111623`
- Sucesso: `True`

## Arquivos copiados
- `backend\app\comic_review_publish\__init__.py`
- `backend\app\comic_review_publish\audit.py`
- `backend\app\comic_review_publish\compat.py`
- `backend\app\comic_review_publish\enums.py`
- `backend\app\comic_review_publish\models.py`
- `backend\app\comic_review_publish\policies.py`
- `backend\app\comic_review_publish\repositories.py`
- `backend\app\comic_review_publish\router.py`
- `backend\app\comic_review_publish\schemas.py`
- `backend\tests\test_comic_review_publish_policies.py`
- `backend\tests\test_comic_review_publish_schemas.py`
- `frontend\src\features\comicReviewPublish\api.ts`
- `frontend\src\features\comicReviewPublish\ApprovalBoard.tsx`
- `frontend\src\features\comicReviewPublish\ChecklistPanel.tsx`
- `frontend\src\features\comicReviewPublish\CommentSidebar.tsx`
- `frontend\src\features\comicReviewPublish\index.ts`
- `frontend\src\features\comicReviewPublish\PublicationWizard.tsx`
- `frontend\src\features\comicReviewPublish\ReleaseHistory.tsx`
- `frontend\src\features\comicReviewPublish\ReviewWorkspace.tsx`
- `frontend\src\features\comicReviewPublish\routes.tsx`
- `frontend\src\features\comicReviewPublish\styles.css`
- `frontend\src\features\comicReviewPublish\types.ts`
- `docs\sprint-16-4\ACCEPTANCE_CRITERIA.md`
- `docs\sprint-16-4\API_EXAMPLES.md`
- `docs\sprint-16-4\SPRINT_16_4_SPEC.md`
- `backend\alembic\versions\0039_comic_review_publish.py`
- `frontend\SPRINT_16_4_FRONTEND_INTEGRATION.md`

## Arquivos integrados
- `backend\app\api\v1\router.py`

## Avisos
- Router frontend nao reconhecido; instrucoes de integracao foram geradas.
- Comando retornou codigo 1: docker compose -f C:\Users\lady_\Downloads\educode-enterprise-2.0-sprint-14\educode-enterprise-2.0-sprint-14\docker-compose.yml run --rm backend sh -lc test ! -f /app/app/operations/preflight.py || python -m app.operations.preflight
- Comando retornou codigo 1: docker compose -f C:\Users\lady_\Downloads\educode-enterprise-2.0-sprint-14\educode-enterprise-2.0-sprint-14\docker-compose.yml run --rm backend sh -lc test ! -f /app/app/operations/migration_check.py || python -m app.operations.migration_check --json

## Rollback

```powershell
.\ROLLBACK-SPRINT-16.4.ps1 -ProjectRoot "CAMINHO_DO_PROJETO"
```
