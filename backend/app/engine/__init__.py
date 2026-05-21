"""
Engine module — Flask engine'in FastAPI içine taşınmış versiyonu.

Migration stratejisi:
1. Her Flask blueprint için FastAPI APIRouter eşi yaz (`routes/`)
2. `core/` içindeki Flask-bağımsız helper'ları olduğu gibi taşı
3. `register_engine_routes(app)` ile main.py'da mount et
4. Frontend'in ENGINE_BASE'ini `/api/engine/` prefix'i kullanacak şekilde güncelle
5. Eski Flask engine'i decommission et (3 server → 1)

Flask → FastAPI çeviri kuralları:
  - `Blueprint(name, __name__)` → `APIRouter(prefix=..., tags=[...])`
  - `@bp.route("/path", methods=["GET"])` → `@router.get("/path")`
  - `request.json` → Pydantic body model (BaseModel)
  - `jsonify(data)` → return dict (auto JSON)
  - `jsonify({"error": ...}), 400` → `raise HTTPException(status_code=400, detail=...)`
  - URL converter `<int:id>` → typed path param `id: int`
"""
