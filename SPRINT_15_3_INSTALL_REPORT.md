# Relatorio de instalacao - Sprint 15.3

- Projeto: `C:\Users\lady_\Downloads\educode-enterprise-2.0-sprint-14\educode-enterprise-2.0-sprint-14`
- Compose: `C:\Users\lady_\Downloads\educode-enterprise-2.0-sprint-14\educode-enterprise-2.0-sprint-14\docker-compose.yml`
- Head anterior: `0032_assessment_delivery`
- Backup: `C:\Users\lady_\Downloads\educode-enterprise-2.0-sprint-14\educode-enterprise-2.0-sprint-14\.sprint-backups\sprint-15-3\20260727-153547`
- Sucesso: `True`

## Arquivos copiados
- `backend\app\instrument_governance\__init__.py`
- `backend\app\instrument_governance\audit.py`
- `backend\app\instrument_governance\compat.py`
- `backend\app\instrument_governance\enums.py`
- `backend\app\instrument_governance\models.py`
- `backend\app\instrument_governance\policies.py`
- `backend\app\instrument_governance\repositories.py`
- `backend\app\instrument_governance\router.py`
- `backend\app\instrument_governance\schemas.py`
- `backend\tests\test_instrument_governance_policies.py`
- `backend\tests\test_instrument_governance_schemas.py`
- `frontend\src\features\instrumentGovernance\api.ts`
- `frontend\src\features\instrumentGovernance\index.ts`
- `frontend\src\features\instrumentGovernance\InstrumentGovernancePage.tsx`
- `frontend\src\features\instrumentGovernance\InstrumentResultsPage.tsx`
- `frontend\src\features\instrumentGovernance\routes.tsx`
- `frontend\src\features\instrumentGovernance\styles.css`
- `frontend\src\features\instrumentGovernance\types.ts`
- `docs\sprint-15-3\ACCEPTANCE_CRITERIA.md`
- `docs\sprint-15-3\API_EXAMPLES.md`
- `docs\sprint-15-3\SPRINT_15_3_SPEC.md`
- `backend\alembic\versions\0033_instrument_governance.py`
- `frontend\SPRINT_15_3_FRONTEND_INTEGRATION.md`

## Arquivos integrados
- `backend\app\api\v1\router.py`

## Avisos
- Router frontend nao reconhecido; instrucoes de integracao foram geradas.
- Comando retornou codigo 1: docker compose -f C:\Users\lady_\Downloads\educode-enterprise-2.0-sprint-14\educode-enterprise-2.0-sprint-14\docker-compose.yml run --rm backend sh -lc test ! -f /app/app/operations/preflight.py || python -m app.operations.preflight

## Rollback

```powershell
.\ROLLBACK-SPRINT-15.3.ps1 -ProjectRoot "CAMINHO_DO_PROJETO"
```
