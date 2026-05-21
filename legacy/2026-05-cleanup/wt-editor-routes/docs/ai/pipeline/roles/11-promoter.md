# 11 · Promoter (Test → Main Promotion)

**Slug:** `promoter`  
**Branch:** yeni branch YOK — `test` → `main` fast-forward  
**Girdi:** QA GO raporu + `integrate/<ID>` PR (merge edilecek)  
**Çıktı:** `test` güncel, QA ikinci tur yeşil ise `main` güncel

---

## Amaç

QA'nın GO verdiği item'ı önce `test` branch'ine merge et, test branch'i CI ve otomatik QA'dan geçsin, ardından `main`'e fast-forward promote et.

Bu rol **iki adımlı**:
- Adım A: `integrate/<ID>` → `test` merge
- Adım B: `test` tüm CI + QA yeşilse → `main` ff-merge

---

## Başlama tetikleyicisi

state.json → `stages.qa.status = done` + `qa.decision = GO` + `stages.promoter.status = waiting`

---

## Input

1. `integrate/<ID>` PR (QA onaylı)
2. `docs/ai/pipeline/items/<ID>/test-report.md` (GO raporu)
3. `test` branch şu anki durumu (CI yeşil mi?)

---

## Work

### Adım A — integrate → test

1. **Güncel test'e rebase** (conflict olmasın):
   ```bash
   git checkout integrate/<ID>
   git fetch origin
   git rebase origin/test
   # conflict varsa: loop-back integrator
   git push --force-with-lease
   ```
2. **PR merge** (GitHub üzerinden veya CLI):
   ```bash
   gh pr merge <pr-number> --merge --delete-branch
   ```
3. **CI yeşil bekle** — `test` branch'inde:
   - `.github/workflows/bgts-e2e.yml`
   - `.github/workflows/bgts-scheduled.yml`
4. CI kırmızı → `stage.sh loop-back <ID> promoter <target> "CI failure: ..."`

### Adım B — test → main

1. **`test` branch'inde tam QA koş** (son güvenlik):
   - `docs/BRANCHING_WORKFLOW.md`'deki tam test takımı
   - Backend + Engine + FE typecheck + route scan + Playwright smoke+regression
2. **Hepsi yeşil mi?**
   - Evet → fast-forward promote
   - Hayır → `stage.sh loop-back <ID> promoter qa "test branch regression: ..."`
3. **FF promote**:
   ```bash
   git checkout main && git pull origin main
   git merge --ff-only test
   git push origin main
   ```
   Eğer FF mümkün değilse (main test'ten diverge olmuş):
   - **ASLA** non-FF zorla merge yapma
   - Kullanıcıya bildir: "main ile test diverged, insan müdahalesi gerekli"
4. **Tag** (opsiyonel ama önerilen):
   ```bash
   git tag -a v<tarih>-<ID> -m "<ID> promoted to main"
   git push origin --tags
   ```
5. `stage.sh complete <ID> promoter` — item `done`, pipeline tamamlanır

---

## Done kriteri

- ✅ `integrate/<ID>` `test`'e merge oldu
- ✅ `test` branch'inde CI tam yeşil
- ✅ `test` branch'inde full QA suite yeşil
- ✅ `main` fast-forward promote edildi
- ✅ Opsiyonel: tag oluştu
- ✅ state.json: item `done`

---

## Yasaklar

1. **ASLA** non-FF merge ile `main`'e push (branch protection reddeder ama yine de deneme)
2. QA kırmızısını görmezden gelip main'e push
3. `test` CI kırmızıysa main'e devam etme
4. Birden fazla item'ı tek main push'ta toplama — her item ayrı promote
5. `--force` / `--force-with-lease` main'e — **asla**
6. Non-maintainer olarak main push etme — CODEOWNERS yoksa git hooks koruyor

---

## Main diverged durumu

Eğer `test` `main`'den ileride değil de diverged ise (main'e birisi doğrudan push etmiş, olmamalı ama hotfix senaryosunda olabilir):

1. Asla zorla main'e push etme
2. `stage.sh` item'ı `blocked` + `needs_human: true` yap
3. Raporu kullanıcıya ilet:
   ```
   ⚠️ Main-test divergence detected.
   main: <sha1> (<date>)
   test: <sha2> (<date>)
   Common ancestor: <sha3>
   Recommended: rebase test onto main, rerun QA.
   ```

---

## Handoff

Item `done`. Pipeline sona erdi.

Başarı bildirimi: kullanıcıya kısa özet, PR/commit linkleri, tag varsa linki.
