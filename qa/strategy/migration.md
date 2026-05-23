# qa/ Migration Planı

3 PR aşamalı, tooling-first, top-down. `BRANCHING_WORKFLOW.md` zorunluluğuna uyumlu: her PR `feature/qa-migration-prN → test → main`.

## PR 1 — İskelet + Tooling (BU PR, ✅ tamamlandı)

**Kapsam:**
- `qa/` klasör yapısı
- `qa/README.md`, `qa/CONVENTIONS.md`
- `qa/package.json` + Node tooling: `validate`, `new-tc`, `trace`, `ai-suggest`
- JSON Schema'lar (`tools/schemas/`)
- Template dosyaları (`templates/`)
- Örnek artifact'ler (TC-AUTH-001, TC-AUTH-002, PRE-001, REQ-AUTH-001, SUITE-AUTH, smoke-daily.yml, R-2026.Q2)
- CI workflow (`.github/workflows/qa-validate.yml`)
- CODEOWNERS stub (`qa/.github-CODEOWNERS`)
- Strategy stub (`strategy/test-strategy.md`, bu dosya)

**Dokunulmayan:**
- `docs/test-analysis/`, `docs/test-design/`, `docs/quality/`, `docs/testing/` — aynen duruyor
- `e2e/bdd/features/`, `backend/tests/bdd/features/`, `engine/features/` — aynen duruyor

**Rollback:** `git revert <merge-sha>` → `qa/` tamamen silinir, hiçbir başka dosya etkilenmemiş olur.

---

## PR 2 — Tasarım dokümanları + features konsolidasyonu

**Kapsam:**

| Hareket | Detay |
|---|---|
| `docs/testing/TEST_STRATEGY.md` → `qa/strategy/test-strategy.md` | Mevcut iskeletin üstüne içerik aktarımı (`git mv`) |
| `docs/quality/*` → `qa/reporting/` + `qa/coverage/` | 7 dosya, `git mv` ile history korunur |
| `docs/test-design/BGTS_*.md` (20+ dosya) → `qa/test-design/` | Tematik MD'ler; isim sadeleştirme (`BGTS_E2E_UI_Test_Scenarios.md` → `e2e-ui.md`) opsiyonel |
| `docs/test-design/features/*.feature` (11 dosya) | **3'ü** (`authentication`, `project_management`, `scenario_management`) `backend/tests/bdd/features/`'ın TR kopyası — silinecek. **8'i** (approvals, bdd_generation, execution_analytics, flows, members_dashboard, regression, requirements_coverage, schedules) → `qa/cases/{domain}/api-scenarios.feature` (design-only) |
| `archive/root-misc/test_scenarios_2026-03-30.feature` + `docs/history/test_scenarios_2026-03-30.feature` | Silinir (placeholder snapshot, bit-identik) |
| `validate.mjs` | **Blocking** moda çevrilir, CI'da fail = merge bloklanır |

**Rollback:** `git mv` reverse edilir, taşınan dosyalar geri eski konumlarına döner.

---

## PR 3 — Manuel TC migration + tag'leme

**Kapsam:**

| Hareket | Detay |
|---|---|
| `docs/test-analysis/manual-test-scenarios.md` (1603 satır) | Parser script (`tools/migrate-manual-scenarios.mjs`, bu PR'da yazılır) ile per-TC `qa/cases/{domain}/TC-*.md`'ye böl |
| **Concat-diff doğrulama** | Split sonrası tüm yeni dosyaları concat edip orijinal 1603 satırla normalized diff → fark sıfır olmalı (CI'da) |
| `e2e/bdd/features/**/*.feature` | Her Scenario'ya `@TC-*` tag'i ekle (manuel + script destekli) |
| `backend/tests/bdd/features/**/*.feature` | Aynı şekilde tag'le |
| `docs/test-analysis/` | Klasör tamamen boşaldıktan sonra silinir |
| `docs/quality/`, `docs/testing/`, `docs/test-design/` | PR 2'de boşaltıldı, bu PR'da silinir |
| Internal link'ler | `grep` + replace ile mevcut MD'lerden `docs/test-analysis/...` referansları `qa/cases/...`'a güncellenir |

**Rollback:** PR2 ve PR3 birlikte revert edilirse eski yapı geri gelir.

---

## PR 4+ (kapsam dışı, ileride)

- `engine/features/` deprecation tamamlanması (65 dosya — pytest-bdd → Cucumber.mjs taşıma)
- `tools/run-record.mjs` (interaktif TUI)
- `tools/import-results.mjs` (Playwright/Cucumber/Allure parser)
- `tools/signoff.mjs` (release sign-off raporu)
- `tools/dashboard.mjs` (statik HTML dashboard)
- `tools/ai-quality.mjs`, `tools/ai-gap.mjs`, `tools/ai-rca.mjs` (PR 5+)
- `apps/web/qa-dashboard` (opsiyonel Next.js sayfası)

## Risk azaltma teknikleri

### 1. Concat-diff doğrulama (PR 3)

```bash
# Split öncesi:
cp docs/test-analysis/manual-test-scenarios.md /tmp/before.md

# Migration script çalıştırılır → qa/cases/**/*.md üretir

# Split sonrası tüm yeni dosyaları normalize edip diff:
cat qa/cases/**/TC-*.md \
  | strip-frontmatter \
  | normalize-whitespace \
  > /tmp/after.md

cat /tmp/before.md | normalize-whitespace > /tmp/before-norm.md

diff /tmp/before-norm.md /tmp/after.md  # fark olmamalı
```

### 2. Concurrent edit lock (PR 2 + PR 3)

CODEOWNERS dosyasına ekleniyor: `docs/test-analysis/manual-test-scenarios.md @yasin-bulgan`. Bu dosya başka bir PR'da değişirse review zorunlu → çakışma erken yakalanır.

### 3. CI gate'leri kademeli

- PR 1: validate.mjs **warn-only**
- PR 2: validate.mjs **blocking**
- PR 3: trace.mjs --check **blocking** (traceability snapshot'lar güncel olmalı)
