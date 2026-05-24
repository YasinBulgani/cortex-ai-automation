# qa/ — Cortex AI Automation İç Kalite Sistemi

> **Git-native test management.** TestRail / Xray / Qase alternatifi olarak repo içinde yaşayan, manuel + otomasyon karması test artifact'lerinin yönetildiği yer.

Bu klasör, **Cortex AI Automation ürününü** test eden iç süreçler içindir. `apps/`, `packages/`, `engine/`, `backend/` ürünün kendisidir; **`qa/` bu ürünü test eden ekibin tutuğu defter**dir.

---

## Hızlı yön bulma

| Klasör | Ne içerir |
|---|---|
| `cases/` | Test case'ler. Her domain (auth, projects, scenarios…) bir klasör, her TC bir `.md` dosyası |
| `plans/` | Test plan YAML'ları (release/cycle bazlı TC seçimleri) |
| `runs/` | Test run kayıtları. `YYYY/MM/TR-*.yml` |
| `milestones/` | Release/version tanımları, exit criteria |
| `shared/pre-conditions/` | Çoklu TC'de paylaşılan önkoşullar (`PRE-*.md`) |
| `shared/steps/` | Tekrar eden adım dizileri (`SS-*.md`) |
| `exploratory/` | Session-based testing notları, charter'lar |
| `defects/` | GitHub Issue mirror'ları (push-after-close); kanonik kaynak GitHub Issues |
| `requirements/` | Gereksinim referansları (`REQ-*.md`) |
| `coverage/` | Otomatik üretilen: `traceability.csv`, `coverage-matrix.md`, `orphans.md` |
| `reporting/` | Şablonlar: exec summary, release sign-off, RCA |
| `strategy/` | Test stratejisi, risk register, tooling dokümanları |
| `test-design/` | Düşük seviye tasarım dokümanları (BGTS_* tematik test kategori dokümanları, PR 2'de taşındı) |
| `templates/` | Yeni artifact oluşturmak için boilerplate'ler |
| `tools/` | CLI: `validate`, `new-tc`, `trace`, `run-record`, `import-results`, `signoff`, `ai-suggest`, `dashboard` |

Konvansiyonlar (ID şeması, frontmatter alanları, naming): **[CONVENTIONS.md](./CONVENTIONS.md)**.

---

## Sık iş akışları

### Yeni TC yaz
```bash
npm run qa:new-tc -- --suite=auth --title="MFA login akışı"
# → qa/cases/auth/TC-AUTH-018-mfa-login-akisi.md (frontmatter doldurulmuş)
```

### Tüm artifact'leri valide et
```bash
npm run qa:validate
# Frontmatter şema + ID benzersizliği + broken reference kontrolü
```

### Traceability üret
```bash
npm run qa:trace
# coverage/traceability.csv + coverage/orphans.md güncellenir
```

### AI ile TC draft (opt-in)
```bash
npm run qa:ai-suggest -- --requirement=REQ-AUTH-005
# → qa/cases/auth/_draft/TC-AUTH-DRAFT-*.md (LLM üretti, human review bekler)
```

### Manuel/otomasyon karma koşum kaydet
```bash
npm run qa:run -- --plan=2026.Q2-release
# Interaktif TUI, sonuçlar runs/YYYY/MM/TR-*.yml
```

---

## Felsefe

1. **Test case'ler kod gibi yaşar**: PR review, branching, history, blame, revert.
2. **Tek kanonik kaynak yoktur, tek kanonik *bağlantı* vardır**: Manuel TC `qa/cases/auth/TC-AUTH-001.md`, otomatik test `e2e/bdd/features/auth/login.feature` — ikisini `@TC-AUTH-001` tag'i birbirine bağlar.
4. **SaaS aracın 22 özelliğini paritede veriyoruz, kaybettiğimiz 3 alan**: glossy UI, real-time görüntü, mobil app. Onları statik HTML dashboard (`tools/dashboard.mjs`) ile kapatıyoruz.
5. **Cortex AI dogfood**: `ai-gateway` ve `packages/ai-sdk` bu kendi QA sistemini test ediyor. AI özellikleri opt-in CLI, CI default'unda çalışmaz (cost rails).

---

## Mimari prensipleri

| Prensip | Pratik karşılığı |
|---|---|
| **Frontmatter machine-readable, body human-readable** | Tooling YAML'ı parse eder, insan markdown'ı okur |
| **ID'ler globally unique** | `TC-AUTH-001` her zaman aynı TC, suite sadece klasör |
| **Run'lar immutable** | Bir kez yazıldı mı değişmez. Re-run = yeni dosya. Git history zaten garantisidir |
| **Defect kanonik = GitHub Issues** | Repo'daki `defects/GH-*.md` sadece close-after-mirror, AI training data |
| **AI özellikleri on-demand** | CI'da default değil. Açık opt-in komut, budget cap'li |
| **CODEOWNERS suite-bazlı** | `qa/cases/auth/` → security team gibi |

---

## Migration durumu

PR sırası (mevcut migration):

| PR | Kapsam | Durum |
|---|---|---|
| **PR 1** | qa/ iskelet + Node tooling + ai-suggest | ✅ Tamamlandı |
| **PR 2** | `docs/test-design/BGTS_*.md`, `docs/quality/`, `docs/testing/` taşıma | ✅ Tamamlandı |
| **PR 3** | `docs/test-analysis/manual-test-scenarios.md` split (1603 satır → 77 TC) | ✅ Tamamlandı |
| **PR 4** | BDD tag (auth/projects/scenarios) + 17 TC automation | ✅ Tamamlandı |
| **PR 5** | BDD tag (approvals/imports/regression/flows) + 9 TC automation | ✅ Tamamlandı |
| **PR 8** | `import-results.mjs` — Playwright/Cucumber/JUnit → run YAML | ✅ Tamamlandı |
| **PR 11** | `run-record.mjs` — interaktif manuel koşum TUI | ✅ Tamamlandı |
| **PR 12** | `dashboard.mjs` — statik HTML dashboard | ✅ Tamamlandı |
| **PR 13** | `signoff.mjs` — release sign-off raporu | ✅ Tamamlandı |
| **PR 6** | executions/a11y BDD eşleştirme (+2 TC automation) | ✅ Tamamlandı |
| **PR 9** | Requirements modülü (23 umbrella REQ-* + 77 TC link) | ✅ Tamamlandı |
| **PR 10** | engine/features/ DEPRECATED.md güncellemesi | ✅ Tamamlandı |
| **PR 14** | Allure-pytest adapter (import-results genişletme) | ✅ Tamamlandı |
| **PR 15** | CI workflow `qa-import-results.yml` (Playwright/Cucumber/JUnit/Allure → run YAML) | ✅ Tamamlandı |
| **PR 16** | GitHub Issues template (`qa-defect.yml`) | ✅ Tamamlandı |
| **PR 17** | Defect mirror workflow + `mirror-defect.mjs` (push-after-close) | ✅ Tamamlandı |
| **PR 18** | Pre-conditions modülü (PRE-002..010, 9 yeni şablonlanmış önkoşul) | ✅ Tamamlandı |
| **PR 19** | `tc-promote.mjs` — AI draft'ları active TC'ye promote | ✅ Tamamlandı |
| **PR 20** | Pre-commit hook (qa-validate + qa-trace-stale) + `qa/INSTALL.md` | ✅ Tamamlandı |
| **PR 21** | `sync-codeowners.mjs` — TC owner'larından `.github/CODEOWNERS` otomatik | ✅ Tamamlandı |
| **PR 22** | REQ-AUTH atomik parçalama pilot (1 umbrella → 3 atomik REQ) | ✅ Tamamlandı |
| **PR 23** | `engine/features/` detay envanteri (read-only rapor, 9 aşamalı roadmap) | ✅ Tamamlandı |
| **PR 24** | REQ atomik parçalama (projects+scenarios+approvals — 6 yeni REQ) | ✅ Tamamlandı |
| **PR 25** | TC pre_conditions bulk eşleştirme (77 TC, 10 PRE) | ✅ Tamamlandı |
| **PR 26** | engine/features/wizard + ai_generated silinmesi (18 dosya → -27%) | ✅ Tamamlandı |
| **PR 27** | `changelog.mjs` — qa-specific git history → CHANGELOG.md | ✅ Tamamlandı |
| **PR 29** | `flakiness.mjs` — run history analyzer | ✅ Tamamlandı |
| **PR 30** | `test-impact.mjs` — PR diff → etkilenen TC raporu | ✅ Tamamlandı |
| **PR 31** | REQ atomik parçalama 2. dalga (executions, syn, regression, imports, schedules — 8 yeni REQ) | ✅ Tamamlandı |
| **PR 32** | `seed-runs.mjs` — demo run YAML üretici (dashboard sanity test) | ✅ Tamamlandı |
| **PR 33** | `strategy/team-handbook.md` — 1 saatlik onboarding rehberi | ✅ Tamamlandı |
| **PR 34** | `strategy/pr34-engine-api-migration.md` — engine/features/api → backend planı | ✅ Tamamlandı |
| **PR 35** | `strategy/pr35-login-feature-merge.md` — duplicate login merge analizi | ✅ Tamamlandı |
| **PR 36** | `apps/web/app/(dashboard)/qa/page.tsx` — Next.js dashboard sayfası | ✅ Tamamlandı |
| **PR 37** | Küçük domain REQ değerlendirmesi (umbrella yeterli, no-op) | ✅ Tamamlandı |
| **PR 38** | `health-check.mjs` — 0-100 sağlık skoru (7 boyut, grade A-F) | ✅ Tamamlandı |
| **PR 39** | `RUNBOOK.md` — 7 incident senaryosu yanıt prosedürü | ✅ Tamamlandı |
| **PR 40** | `regression-detect.mjs` — PR risk skoru + merge tavsiye | ✅ Tamamlandı |

Migration detayı: [strategy/migration.md](./strategy/migration.md).

---

## İlişki: `qa/` vs `apps/`, `engine/`, `e2e/`

```
┌────────────────────────────────────────────────┐
│  qa/  ← Bu klasör. İç QA süreçlerimiz.        │
│       Test case'ler, plan, run, traceability.  │
└─────────────────┬──────────────────────────────┘
                  │ referans verir (read-only)
                  ▼
┌────────────────────────────────────────────────┐
│  e2e/, api-tests/, backend/tests/, engine/     │
│  ← Otomasyon kodu (Playwright, pytest, …)      │
│  @TC-* tag'leri ile qa/cases/'a bağlanır.      │
└─────────────────┬──────────────────────────────┘
                  │ test eder
                  ▼
┌────────────────────────────────────────────────┐
│  apps/, packages/, engine/src, backend/app     │
│  ← Ürün kodu.                                  │
└────────────────────────────────────────────────┘
```

`qa/` ürün kodunu **doğrudan** test etmez. Otomasyon katmanı (`e2e/`, `api-tests/`, …) test eder; `qa/` o testleri **yönetir, izler, raporlar**.

---

## Lisans ve katkı

Bu klasör Cortex AI Automation projesinin parçasıdır. Katkı yönergeleri için kök dizindeki [CONTRIBUTING.md](../CONTRIBUTING.md) ve [BRANCHING_WORKFLOW.md](../docs/BRANCHING_WORKFLOW.md) geçerlidir.
