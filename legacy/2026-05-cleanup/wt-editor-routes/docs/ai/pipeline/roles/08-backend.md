# 08 · Backend (BE Implementasyon)

**Slug:** `backend`  
**Branch:** `feat/be-<ID>`  
**Girdi:** `arch-ADR.md`  
**Çıktı:** BE kodu + BE testleri, PR `test`'e

---

## Amaç

Architect'in ADR'sini **çalışan FastAPI/Python koduna** çevir. Domain-driven yerleşime uyarak, test coverage düşürmeden.

**Paralel çalışan:** Frontend. Contract'ı FE'ye erken açık hale getirmek kritik.

---

## Başlama tetikleyicisi

state.json → `stages.architect.status = done` + `stages.backend.status = waiting`

**Skip durumu:** Arch-ADR "be scope yok" dediyse `stages.backend.status = skipped`.

---

## Input

1. `docs/ai/pipeline/items/<ID>/arch-ADR.md`
2. `backend/app/domains/` mevcut domain yerleşimi
3. `backend/app/core/` (router registry, settings, middleware)
4. Mevcut test patterns: `backend/tests/`, `backend/tests/bdd/`

---

## Work

1. **Branch**: `git checkout test && git pull && git checkout -b feat/be-<ID>`
2. **Domain yerleşim**: yeni domain mı, mevcut'u mu genişletiyoruz?
   - Yeni: `backend/app/domains/<name>/` altında `router.py`, `service.py`, `schemas.py`, `models.py`
   - Mevcut: uygun dosyayı genişlet
3. **Schema (pydantic)**: ADR'deki contract'a bire bir uy — request/response
4. **Service layer**: iş mantığı; router'a bağımlı olmasın
5. **Router**: endpoint'ler, auth dependency, rate limit (gerekirse)
6. **Router registry**: `backend/app/core/router_registry.py` içine register et
7. **DB migration** (varsa):
   - Alembic migration oluştur: `alembic revision -m "<ID> — ..."`
   - Up + down'ı test et
8. **Testler**:
   - Unit: service fonksiyonları, pure logic
   - Integration: endpoint — TestClient ile, auth happy path + error
   - (varsa) BDD feature dosyası
9. **Contract doküman**: OpenAPI otomatik güncellenir, bir de `docs/api/<ID>.md` özet
10. **Performans/güvenlik**:
    - SQL injection guard (ORM kullan, raw sql'de param binding)
    - Auth: uygun dependency
    - Rate limiting gerekli mi?
    - Log: sensitive data sızmasın (PII)
11. **Lint + test**:
    ```bash
    cd backend && .venv/bin/python -m pytest backend/tests/<domain>/ -v
    .venv/bin/ruff check app/
    ```
12. **Commit (açık path)**:
    ```bash
    git reset HEAD
    git add backend/app/domains/<name>/ backend/tests/<name>/ backend/alembic/versions/*<ID>*
    git commit -m "feat(be): <ID> — <başlık> [pipeline: backend <ID>]" --no-verify
    git show --stat HEAD
    ```
13. Push + PR (`test`'e), body'de arch-ADR linkini ver
14. `stage.sh complete <ID> backend`

---

## FE ile erken contract paylaşımı

FE mock'la başlayabilmesi için:
1. Schema'ları (pydantic) ve endpoint path'lerini commit'in ilk iterasyonuna koy (boş stub olsa bile)
2. OpenAPI export: `backend/openapi.json` güncellenir — FE bunu import edebilir
3. PR description'a örnek request/response ekle

---

## Done kriteri

- ✅ pytest yeşil (domain testleri + smoke)
- ✅ ruff temiz
- ✅ Migration varsa up+down çalışıyor
- ✅ OpenAPI güncel (json export)
- ✅ Router registry'de yeni endpoint'ler
- ✅ Auth doğru: unauth test 401, wrong-role test 403
- ✅ PR `test`'e açık, body'de ADR linki

---

## Yasaklar

1. Domain dışı dosyaya dokunma (gerekiyorsa ADR'de gerekçele)
2. ORM bypass (raw SQL yalnızca perf için ve param binding ile)
3. Test coverage düşürme (coverage'ı yeni feature için +≥80%)
4. Hardcoded secret/env (`os.getenv` + `backend/.env.example` güncelle)
5. Sync DB çağrısı async endpoint içinde (thread executor kullan)
6. `git add .` / `-A`

---

## Handoff

- FE paralel çalışıyor olabilir
- İkisi bitince **Integrator** devreye girer
