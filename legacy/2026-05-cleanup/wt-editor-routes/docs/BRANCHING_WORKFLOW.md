# Branching & Promotion Workflow

> **Özet**: `feature/*` → `test` → `main` (prod). Hiçbir geliştirici doğrudan
> `main`'e push atmaz; her değişiklik **önce `test` branch'inde QA agent
> tarafından** doğrulanır, ardından promote edilir.

---

## 🌳 Branch Rolleri

| Branch | Rol | Kim push atar? |
|--------|-----|----------------|
| `main` | **Production.** Deploy edilen sürüm. | Sadece `test`'ten fast-forward / merge ile. |
| `test` | **Staging / Integration.** QA agent burada tam test takımını çalıştırır. | Tüm geliştiriciler (PR veya direct). |
| `feature/*`, `fix/*`, `chore/*` | Kişisel / görev bazlı çalışma. | Sahibi. |
| `claude/*` | AI agent oturum branch'leri. | İlgili agent. |

---

## 🔁 Günlük Akış

```
┌───────────────┐    PR   ┌──────┐   QA agent OK   ┌──────┐
│ feature/xyz   ├────────▶│ test │────────────────▶│ main │
└───────────────┘         └──────┘                 └──────┘
       ▲                      │
       │ herkes buraya atar   │
       │                      └── failing? → ilgili sahibine bildir
       │                                      düzeltme yeni PR
```

### 1. Geliştirici adımı

```bash
# Temiz bir başlangıç
git checkout test
git pull origin test

# Kendi dalını aç
git checkout -b feature/odeme-ekrani

# Çalış, commit'le, push'la
git commit -am "feat(payment): şu alanları ekle"
git push origin feature/odeme-ekrani

# GitHub'da `feature/odeme-ekrani → test` PR'ı aç (hedef main DEĞİL)
```

Alternatif (merge sorumlusu geliştiriciyse): doğrudan `test`'e push ok.

### 2. QA Agent adımı (`test` branch'inde)

Her `test` push'undan sonra QA agent otomatik olarak koşturur:

| Aşama | Komut | Başarı kriteri |
|---|---|---|
| Backend smoke | `npm run test:backend:smoke` | 0 fail |
| Backend tam | `cd backend && .venv/bin/python -m pytest --ignore=tests/bdd` | 0 fail |
| Engine tam (non-ai) | `cd engine && .venv/bin/python -m pytest tests/ -m 'not ai' --ignore=tests/e2e` | 0 fail |
| Frontend typecheck | `cd apps/web && npx tsc --noEmit` | 0 hata |
| Frontend route scan | 80+ sayfa HTTP 200 (scripts/page_scanner.py) | tümü 200 |
| Playwright smoke | `npm run test:e2e:smoke` | 0 fail (skip OK) |
| Playwright regression | `npm run test:e2e:regression` | 0 fail (flaky ≤ 1) |

QA agent raporu `reports/qa-agent-<timestamp>.md` altına yazar ve `test`
branch'ine commit'ler.

### 3. Promotion (`test` → `main`)

**QA agent yeşil raporu verirse** (sahibi onayıyla):

```bash
# Lokal maintainer veya GitHub Actions
git checkout main
git pull origin main
git merge --ff-only test       # fast-forward önerilen; merge commit istenirse --no-ff
git push origin main
```

**Kırmızıysa**: `main` güncellemesi YOK. Bulgular ilgili PR sahibine
issue / comment olarak bildirilir, `test` branch'i düzeltmeyi bekler.

---

## 🚦 Branch Koruma Kuralları (GitHub Settings → Branches)

### `main`
- [x] Require pull request before merging
- [x] Require status checks to pass:
  - `qa-agent / backend-tests`
  - `qa-agent / engine-tests`
  - `qa-agent / playwright-smoke`
- [x] Require branches to be up to date
- [x] Restrict pushes that create matching branches (yalnızca maintainer)
- [x] Do not allow force push

### `test`
- [x] Require status checks to pass:
  - `qa-agent / backend-tests`
  - `qa-agent / engine-tests`
- [ ] PR gerekmez (hız için direct push kabul)
- [x] Do not allow force push

---

## 🤝 Çatışma (Merge Conflict) Kuralı

Birden fazla kişi `test`'e push attığında conflict doğabilir.
Conflict'i, **conflict'i yaratan kişi** kendi feature branch'inde
`git merge test` ile çözer ve yeniden PR / push atar. QA agent, sorunsuz
merge edilememiş PR'ları otomatik olarak reddeder.

---

## 🔒 Hotfix

Üretimde kritik bug için:

```bash
git checkout main
git pull
git checkout -b hotfix/xyz
# düzelt, commit, push
# test'e PR (normal akış), sonra main'e promote
```

Acil durumlarda (>P0) maintainer `main`'e doğrudan fast-forward merge
yapabilir, ama `test` branch'i aynı anda senkronlanmalı:

```bash
git checkout test
git merge main
git push origin test
```

---

## 📋 Checklist (PR açarken)

- [ ] Branch hedefi `test` (main DEĞİL)
- [ ] Commit mesajları conventional commits (`fix(...):`, `feat(...):`)
- [ ] Lokal olarak `npm run test:backend:smoke` yeşil
- [ ] Lokal olarak `cd apps/web && npx tsc --noEmit` temiz
- [ ] PR açıklamasında "Neden" + "Test planı" var

---

## 🗓️ Son güncelleme

- **Tarih**: 2026-04-19
- **Sahibi**: QA Agent + Yasin Bulgan
