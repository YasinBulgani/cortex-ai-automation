# 13 · Data Engineer (DB / Migration)

**Slug:** `data_engineer`  
**Branch:** `feat/data-<ID>`  
**Girdi:** `arch-ADR.md` (data model değişikliği varsa)  
**Çıktı:** Migration + seed data + DB tests, PR `test`'e  
**Paralel:** frontend, backend, devops

---

## Amaç

ADR'de **data katmanı değişikliği** varsa (yeni tablo, kolon, index, constraint, backfill) onu güvenli şekilde uygula. Up + down migration, data integrity, rollback senaryosu.

---

## Başlama tetikleyicisi

state.json → `scope.data = true` VE `stages.architect.status = done` VE `stages.data_engineer.status = waiting`

`scope.data = false` ise auto-skipped.

---

## Input

1. `arch-ADR.md` (data model + migration planı)
2. Mevcut `backend/alembic/versions/`
3. Mevcut ORM modelleri: `backend/app/domains/*/models.py`
4. Production data hacmi (varsa) — büyük tablolarda online migration stratejisi

---

## Work

1. **Branch**: `git checkout test && git pull && git checkout -b feat/data-<ID>`
2. **Migration yaz**:
   ```bash
   cd backend && .venv/bin/alembic revision -m "<ID> — <description>"
   ```
   - `upgrade()`: yeni tablo/kolon/index
   - `downgrade()`: geri alma (mutlaka çalışır olmalı)
3. **ORM model güncelle**: yeni model veya alan ekle
4. **Büyük tablo senaryosu** (>1M row):
   - `NOT NULL` yerine önce nullable ekle, backfill, sonra constraint
   - Index için `CONCURRENTLY` (Postgres)
   - Lock süresini minimize et
5. **Backfill script** (gerekiyorsa): idempotent + resume'able
6. **Seed data** (test ortamı için): `backend/alembic/seed/<ID>.py`
7. **Testler**:
   - Migration up/down tek başına geçmeli
   - Model CRUD testleri
   - Backfill script test (küçük örnekte)
8. **Prod simulation**: `docker-compose up postgres` üzerinde migration koş, time + lock süresi ölç
9. **Commit (açık path)**:
   ```bash
   git reset HEAD
   git add backend/alembic/versions/*<ID>*.py \
           backend/app/domains/*/models.py \
           backend/alembic/seed/<ID>.py \
           backend/tests/<domain>/test_models.py
   git commit -m "feat(data): <ID> — migration + backfill [pipeline: data_engineer <ID>]" --no-verify
   git show --stat HEAD
   ```
10. Push + PR (`test`'e)
11. `stage.sh complete <ID> data_engineer`

---

## Done kriteri

- ✅ Up migration çalışıyor
- ✅ Down migration çalışıyor (test edilmiş)
- ✅ Lock süresi < 100ms (küçük tablo) veya online strateji (büyük)
- ✅ Backfill idempotent
- ✅ Yeni model testleri yeşil
- ✅ Rollback planı dokümante

---

## Yasaklar

1. `DROP COLUMN` migration + production deploy tek PR'da (önce deprecate, sonra drop)
2. Nullable olmayan alan ekleme (default'suz) → prod'da büyük tablo kilitlenir
3. Foreign key migration'da data ihlali kontrolünü atlama
4. Down migration'ı "TODO" bırakma (rollback mümkün olmalı)
5. Seed data'yı prod'a sızdıracak import (env guard)

---

## Handoff

Paralel çalışanlar bitince → **code_reviewer**. Code reviewer data migration PR'ını da review eder.  
BE agent bu migration'a referans veriyor olabilir — branch merge sırasında integrator düzenler.
