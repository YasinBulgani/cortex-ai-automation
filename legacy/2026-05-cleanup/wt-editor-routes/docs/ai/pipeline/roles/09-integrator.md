# 09 · Integrator (FE + BE Birleştirme)

**Slug:** `integrator`  
**Branch:** `integrate/<ID>` (test'ten türetilir, FE + BE merge edilir)  
**Girdi:** `feat/fe-<ID>` + `feat/be-<ID>` branch'leri  
**Çıktı:** birleştirilmiş PR `test`'e

---

## Amaç

FE ve BE'nin birbirini doğru tanıdığından emin ol: contract uyumlu mu, mock yerine gerçek endpoint bağlandı mı, smoke scenario çalışıyor mu?

---

## Başlama tetikleyicisi

state.json → `stages.frontend.status in [done, skipped]` + `stages.backend.status in [done, skipped]` + `stages.integrator.status = waiting`

Eğer ikisi de `skipped` ise integrator da `skipped`, direkt QA'ya.

---

## Input

1. FE PR (`feat/fe-<ID>`)
2. BE PR (`feat/be-<ID>`)
3. `arch-ADR.md` (contract referansı)

---

## Work

1. **Test'ten türet**:
   ```bash
   git checkout test && git pull && git checkout -b integrate/<ID>
   ```
2. **BE'yi merge et**:
   ```bash
   git merge --no-ff feat/be-<ID> -m "chore: merge BE for <ID>"
   ```
3. **FE'yi merge et**:
   ```bash
   git merge --no-ff feat/fe-<ID> -m "chore: merge FE for <ID>"
   ```
4. **Conflict çözümü**: varsa — öncelik arch-ADR'de; kuşkulu noktada architect'i PR yorumunda mention et
5. **Mock → gerçek geçiş** (FE mock'la çalıştıysa):
   - `.env.local` mock flag'ini `USE_MOCK=0`
   - FE'deki mock import'ları gerçek API çağrılarına çevir
   - Yaptığın değişiklikleri tek commit: `[pipeline: integrator <ID>]`
6. **Smoke çalıştır** (lokal):
   ```bash
   make docker-up
   cd backend && .venv/bin/uvicorn app.main:app --port 8000 &
   cd apps/web && npm run dev -- --port 3000 &
   # critical path senaryosu — ADR'deki "user flow"dan
   ```
7. **Contract diff kontrol**:
   - OpenAPI: `backend/openapi.json` güncel mi?
   - FE'de beklenen response şeması ile BE'nin verdiği eşleşiyor mu?
   - Ripcord test: `curl http://localhost:8000/api/...` ile manuel bir kez
8. **Typecheck + lint** her iki tarafta:
   ```bash
   cd apps/web && npx tsc --noEmit
   cd backend && .venv/bin/ruff check app/
   ```
9. **Contract uyumsuzluğu varsa** → `stage.sh loop-back <ID> integrator <fe|be> "<reason>"`
10. **Temizse** push + PR:
    ```bash
    git push -u origin integrate/<ID>
    gh pr create --base test --title "integrate: <başlık> [<ID>]" --body "..."
    ```
11. `stage.sh complete <ID> integrator`

---

## Done kriteri

- ✅ Merge conflict yok (çözülmüş)
- ✅ Mock kullanılmıyorsa contract uyumlu
- ✅ FE tsc 0 hata, BE ruff 0 hata
- ✅ Smoke scenario çalışıyor (arch-ADR user flow)
- ✅ PR `test`'e açık
- ✅ PR body'de: FE PR linki, BE PR linki, arch-ADR linki

---

## Yasaklar

1. Conflict'i rasgele çözme — ADR'ye dan
2. Mock'u prod'a bırakma (`.env.local` flag kontrol)
3. Tek taraflı squash — FE/BE'nin commit history'si korunsun (`--no-ff`)
4. Yeni özellik ekleme (integrator bu değildir)
5. Test atlama (smoke mutlaka)

---

## Handoff

Sonraki: **QA**. state.json → `qa.status = waiting`, `qa.branch = qa/<ID>` açılacak.

QA kırmızı verirse ilgili tarafa (FE/BE) loop-back; sen tekrar merge edersin.
