# ADR 0005: Flask Engine → FastAPI Consolidation

**Status**: In Progress (Pattern Established)
**Date**: 2026-05-14

## Context

3 ayrı Python servisi:
```
FastAPI :8000  (backend)
Flask   :5001  (engine)     ← konsolide edilecek
FastAPI :8080  (ai-gateway) ← konsolide edilecek
```

**Sorunlar**:
- 3 ayrı deploy + monitoring
- Inter-service auth (X-Internal-Key shared secret)
- Python version mismatch riski
- Flask/FastAPI hibrit codebase

## Decision

Engine ve ai-gateway'i tek FastAPI backend altında modül olarak topla:

```
backend/app/
├─ engine/          ← Flask'tan port
│  ├─ routes/       ← Her Flask blueprint = APIRouter
│  └─ core/         ← Flask-bağımsız helper'lar
└─ services/ai/     ← ai-gateway'den port
```

## Migration Pattern

Flask → FastAPI çeviri kuralları:

| Flask | FastAPI |
|-------|---------|
| `Blueprint("x", __name__, url_prefix="/api/x")` | `APIRouter(prefix="/api/x", tags=["x"])` |
| `@bp.route("/path", methods=["GET"])` | `@router.get("/path")` |
| `request.json` | Pydantic body model parameter |
| `jsonify(data)` | `return data` (auto JSON) |
| `jsonify({"error": ...}), 400` | `raise HTTPException(400, detail=...)` |
| `<int:id>` URL converter | typed path param `id: int` |
| `@app.before_request` | dependency injection |

## Status

**Phase 1**: Pattern proven (✅ done — `regression_routes` migrated)
- 7/7 tests passing
- Same API contract preserved

**Phase 2**: Remaining 36 Flask routes (in priority order):
1. lifecycle, manual, regression ✓
2. webhook, auth (consolidate with /api/v1/auth)
3. ai_generation, ai_analysis, ai_healing
4. runner, banking, datasim
5. mobile, device_manager, monkey
6. wizard, editor, ...

**Phase 3**: Decommission Flask engine
- Update frontend `ENGINE_BASE` → `/api/engine/`
- Stop port 5001
- Remove `engine/` directory

## Verification

```bash
cd backend && ./.venv/bin/python -m pytest app/engine/routes/tests/
# → 7 passed
```

Frontend continues working: routes are at `/api/regression-sets` (same as before).
