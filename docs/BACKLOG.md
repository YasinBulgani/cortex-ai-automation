# Cortex AI Automation — Açık Backlog

**Snapshot tarihi:** 2026-05-24 (son güncelleme: P3 devam)
**Branch:** `feature/qa-system-bootstrap`

---

## Son Sprint Commit'leri (kapalı, referans)

| Commit | Madde | Konum |
|---|---|---|
| `e2f16a3` | Recorder #1–4 (alias, soft-fail, atomic save, hata mesajı) | `frameworks/cortex-java/...` |
| `bcee297` | Recorder #7 ${ENV:VAR} CI override | `DecryptUtil.java` |
| `1295dd8` | Recorder #8 pre-flight credential check | `CredentialPreflightChecker.java` |
| `f1a4d02` | B6 playwright-mcp 5 endpoint aliases | `playwright_mcp/router.py` |
| `db806b3` | R1 monkey/page.tsx (1980→1455 LOC) | |
| `6c86815` | R2 mobil-otomasyon/page.tsx (1386→1047 LOC) | |
| `0e582e9` | R3 api-testing/page.tsx (981→940 LOC) | |
| `ba911df` | R4+R5 playwright-console (1031→962) + locators (1107→1031) | |
| `85ed83a` | Neurex Management backend domain | `backend/app/domains/test_management/` |
| `83d2931` | Neurex Management frontend (11 pages) | `management/` pages |
| `9320cdb` | Test coverage batch 1 | `backend/tests/unit/` |
| `fec7947` | Docs, engine, e2e, framework improvements | |
| `1a8f352` | Recorder #5 password mask + alias confirm UI | `recorder-extension/` |
| `5531dbe` | Recorder #6 per-feature credential vault | `FeatureVault.java`, `VaultContext.java` |
| `a890ce4` | M1 management dashboard live API | `management/page.tsx` |
| `58ffc5d` | M2 run execute interactive step result flow | `runs/[runId]/execute/page.tsx` |
| `d23830c` | M3+M4 evidence upload + import staging | `import-export/page.tsx` |
| `0e75cfb` | M5 requirements traceability matrix | `requirements/page.tsx` |
| `bf3d144` | router registry, integration tests, CHANGELOG | |
| `380f092` | P3-RLS test_management_* tabloları (15 tablo, 3-tier strateji) | `alembic/versions/20260524_0003` |
| `0a99dc0` | P3-i18n TR/EN translation context + LanguageSwitcher | `lib/i18n/`, ADR 0008 |
| `4e3d828` | P3-SDK @cortex/sdk TypeScript public API SDK | `packages/sdk/` |
| `fc0469b` | P3-Onboarding 6. adım (Neurex Mgmt) + language switcher | `onboarding/page.tsx` |
| `1396a3b` | P3-Storybook Management + Onboarding stories | `apps/storybook/stories/` |
| `992dad8` | P3-RAG Semantic case similarity search (AI Gateway embed) | `semantic_search.py`, repository/page |
| `ff9e151` | P3-DevFarm Device farm adapters (AWS/BrowserStack/Sauce/Local) | `device_farm_adapters.py`, `/farm/*` routes |
| `4b62a10` | P3-DevFarm Device farm frontend UI | `device-farm/page.tsx` |
| `1a6dda2` | Tests: semantic search + device farm adapters (30+ unit tests) | `tests/unit/` |
| `5d6a67c` | P3-SSO/MFA TOTP-based 2FA (setup/verify/disable/backup codes) | `mfa_service.py`, `/auth/mfa/*` routes, `/settings/security` |

---

## ✅ Tüm Backlog Kapatıldı (P1 + P2)

Tüm P1 ve P2 maddeleri önceki sprintlerde kapatıldı.

---

## ✅ P3 Tamamlananlar

| # | Madde | Commit |
|---|---|---|
| P3-1 | Multi-tenant RLS (test_management_* 15 tablo) | `380f092` |
| P3-2 | i18n infrastructure (TR/EN, useT hook, LanguageSwitcher) | `0a99dc0` |
| P3-3 | Public API & SDK (@cortex/sdk TypeScript package) | `4e3d828` |
| P3-4 | Onboarding Wizard güncelleme (6. adım + language switcher) | `fc0469b` |
| P3-5 | Storybook stories (Management domain + Onboarding) | `1396a3b` |
| P3-6 | RAG/Vector DB (semantic case search, AI Gateway embeds) | `992dad8` |
| P3-7 | Device Farm Integration (4 providers + frontend UI) | `ff9e151`, `4b62a10` |
| P3-8 | SSO/MFA — TOTP 2FA (RFC 6238, backup codes, frontend wizard) | `5d6a67c` |
| P3-9 | Marketing landing page (hero, features, pricing, footer) | `eb1c9a7` |

---

## ✅ P3-10 — SOC 2 / DPA evidence (TAMAMLANDI)

| Commit | Madde | Konum |
|---|---|---|
| `69d48b3` | Bug fix: test failures + Python 3.9 compat | `semantic_search.py`, `device_farm_adapters.py`, `brain.py` |
| `e6b1519` | P3-SOC2 Audit log export + DPA templates | `audit/router.py`, `docs/compliance/` |
| `d958082`–`dca87e7` | Test coverage expansion (700+ new pure-helper unit tests, 7126 total) | `backend/tests/unit/` |

**Ne yapıldı:**
- `GET /audit/export/json` — hash-chain alanları dahil tam JSON export
- `GET /audit/export/csv` — seq/prev_hash/hash sütunları dahil CSV
- `GET /audit/export/summary` — tarih aralığında event sayısı
- Admin audit sayfası: tarih filtresi, JSON/CSV indirme butonları, IP + Sıra # sütunları
- `docs/compliance/DPA-template-TR.md` — KVKK Madde 12 / GDPR Madde 28 DPA şablonu
- `docs/compliance/DPA-template-EN.md` — İngilizce DPA şablonu
- `docs/compliance/SOC2-controls-mapping.md` — CC1/CC2/CC3/CC6/CC7/CC8/CC9 kontrol haritası
- 20 yeni unit test (`test_audit_export.py`)

---

## ✅ Tüm Backlog Kapatıldı

Tüm P1, P2 ve P3 maddeleri tamamlandı.

> Billing (Stripe) — zaten tamamlanmış (billing domain 1283 LOC + /admin/billing page)
> Cookie banner — `6c385de` ile tamamlandı

---

## Kullanım Notu

- Bir maddeye başlarken: `git log -p` ile son commit'lerde değişip değişmediğini kontrol et.
- Yeni bulgu çıkarsa: `BACKLOG.md`'ye **dosya:satır referansıyla** ekle.
- Kapatınca: tablodan sil + commit mesajında madde kodunu belirt.
