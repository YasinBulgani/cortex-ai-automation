# qa/ — Konvansiyonlar

Bu doküman normatiftir. `tools/validate.mjs` buradaki kuralları uygular.

---

## 1. ID Şeması

| Artifact | Pattern | Örnek |
|---|---|---|
| Test Case | `TC-{DOMAIN}-{###}` | `TC-AUTH-001` |
| Suite | `SUITE-{DOMAIN}` | `SUITE-AUTH` (klasör tabanlı, `_suite.yml` içinde) |
| Pre-condition | `PRE-{###}` | `PRE-001` |
| Shared Step | `SS-{###}` | `SS-001` |
| Requirement | `REQ-{DOMAIN}-{###}` | `REQ-AUTH-001` |
| Test Plan | `TP-{RELEASE}-{NAME}` | `TP-2026.Q2-RELEASE` |
| Milestone | `R-{YYYY}.{QN}` | `R-2026.Q2` |
| Test Run | `TR-{YYYY}-{MM}-{DD}-{NAME}-{###}` | `TR-2026-05-22-SMOKE-001` |
| Defect (mirror) | GitHub Issue numarası | `GH-1234` (dosya: `defects/GH-1234.md`) |
| Exploratory charter | `EXP-{YYYY}-{MM}-{DD}-{slug}` | `EXP-2026-05-22-llm-agent` |

**Defect ID'leri GitHub Issues'tan gelir** (push-after-close mirror). Lokal `DEF-*` ID'si yoktur.

---

## 2. Domain prefix kayıt listesi

Yeni domain eklemek = PR. Aşağıdaki liste `tools/validate.mjs`'te enum olarak kayıtlıdır:

| Prefix | Domain |
|---|---|
| `AUTH` | Authentication / authorization, MFA, session |
| `PRJ` | Project management |
| `SCN` | Scenario authoring + management |
| `EXC` | Execution engine, test run lifecycle |
| `APR` | Approvals, review queues |
| `RBAC` | Role-based access, permissions |
| `FLW` | Flow / pipeline orchestration |
| `INT` | External integrations (Jira, Slack, …) |
| `API` | API test platform (api-tests/) |
| `RPT` | Reporting, dashboards |
| `ADM` | Admin tools, settings |
| `BIL` | Billing, subscriptions |
| `NTF` | Notifications |
| `SCH` | Scheduling, cron |
| `IMP` | Import (TC ingestion from external) |
| `REG` | Regression suite management |
| `REQ` | Requirements module |
| `MEM` | Member / user management |
| `DASH` | Dashboard UI |
| `BDD` | BDD generation features |
| `AI` | AI features (LLM agent, smart suggest) |
| `MOB` | Mobile / responsive |
| `A11Y` | Accessibility |
| `PERF` | Performance |
| `SEC` | Security |
| `SYN` | Synthetic data (test data generation) |
| `ENG` | Engine (Flask backend test runner) |
| `VIS` | Visual regression |
| `REC` | Test recorder |
| `DSM` | DataSim (data simulation) |
| `INF` | Infrastructure (health, observability) |
| `QA` | QA Engine (backend QA routes) |
| `RUN` | Test run lifecycle (execution layer) |

Yeni prefix eklemek: bu tabloyu güncelle + `tools/lib/domains.mjs`'i güncelle. PR review zorunludur.

---

## 3. Frontmatter şemaları

### 3.1 Test Case (`cases/{domain}/TC-*.md`)

```yaml
---
id: TC-AUTH-001                    # zorunlu, globally unique, ID şemasına uygun
title: "Geçerli kimlik..."         # zorunlu
suite: auth                        # zorunlu, klasör adıyla aynı
priority: P0                       # zorunlu: P0 | P1 | P2 | P3
type: [functional, smoke]          # zorunlu, en az 1: functional | smoke | regression | integration | api | ui | perf | security | a11y | exploratory
status: active                     # zorunlu: draft | active | deprecated
owner: "@username"                 # zorunlu
created: 2026-05-22                # zorunlu, ISO 8601 date
updated: 2026-05-22                # zorunlu
estimated_minutes: 3               # opsiyonel
automation:
  status: automated                # zorunlu: not-automated | in-progress | automated | out-of-scope
  reason: ""                       # status=out-of-scope ise zorunlu
  refs:                            # status=automated ise zorunlu, en az 1
    - e2e/bdd/features/auth/login.feature:12
    - e2e/login.spec.ts:8
requirements: [REQ-AUTH-001]       # opsiyonel
pre_conditions: [PRE-001]          # opsiyonel
tags: [auth, login, p0]            # opsiyonel
configurations:                    # opsiyonel
  browsers: [chromium, firefox]
  envs: [staging, prod]
data_sets: []                      # opsiyonel, data-driven TC için referans
open_defects: [GH-1234]            # opsiyonel, GitHub Issue ID'leri
---
```

### 3.2 Suite (`cases/{domain}/_suite.yml`)

```yaml
id: SUITE-AUTH                     # zorunlu
title: "Kimlik Doğrulama"          # zorunlu
description: ""                    # zorunlu
domain: identity                   # zorunlu, semantik etiket
owner: "@username"                 # zorunlu (CODEOWNERS ile tutarlı)
parent: null                       # opsiyonel, parent suite ID
order: 1                           # opsiyonel, sıralama hint'i
links:
  spec: "../../requirements/REQ-AUTH-001-login-spec.md"
  bdd_ui: "../../../e2e/bdd/features/auth/"
  bdd_api: "../../../backend/tests/bdd/features/authentication.feature"
```

### 3.3 Test Plan (`plans/*.yml`)

```yaml
id: TP-2026.Q2-RELEASE             # zorunlu
title: ""                          # zorunlu
milestone: R-2026.Q2               # zorunlu
owner: "@username"                 # zorunlu
created: 2026-05-15                # zorunlu
scope:
  include:                         # en az 1 girdi
    - suite: auth
      priorities: [P0, P1]
    - cases: [TC-RBAC-007]
  exclude:                         # opsiyonel
    - tags: [deprecated]
configurations:                    # opsiyonel
  matrix:
    - { browser: chromium, env: staging }
exit_criteria:                     # zorunlu, en az 1
  - "Tüm P0 pass"
  - "P1 fail oranı < %5"
```

### 3.4 Test Run (`runs/YYYY/MM/TR-*.yml`)

```yaml
id: TR-2026-05-22-SMOKE-001        # zorunlu, immutable
plan: smoke-daily                  # zorunlu, plan ID veya plan file name
started: 2026-05-22T09:15:00+03:00 # zorunlu, ISO 8601
ended: 2026-05-22T09:22:00+03:00   # zorunlu
executor: "@username"              # zorunlu, manuel run için
environment:                       # zorunlu
  branch: main
  commit: 4f8a9c2
  browser: chromium
  env: staging
summary:                           # zorunlu
  total: 24
  passed: 22
  failed: 1
  blocked: 1
  skipped: 0
  untested: 0
results:                           # zorunlu, en az 1
  - tc: TC-AUTH-001                # zorunlu
    tc_commit: 4f8a9c2             # zorunlu, immutability için
    status: pass                   # zorunlu: pass | fail | blocked | skipped | untested | retest | not-applicable
    duration_s: 3.2                # opsiyonel
    automation: e2e/login.spec.ts:8 # opsiyonel, otomasyon kullanıldıysa
    defect: GH-1234                # opsiyonel, fail/blocked durumunda
    note: ""                       # opsiyonel
    evidence: "evidence/TR-2026-05-22/TC-AUTH-001.png"  # opsiyonel
```

### 3.5 Defect Mirror (`defects/GH-*.md`)

```yaml
---
id: GH-1234                        # GitHub Issue numarası
title: ""                          # zorunlu
severity: S2                       # zorunlu: S1 | S2 | S3 | S4
status: closed                     # mirror sadece closed durumunda yazılır
found_in: TR-2026-05-22-SMOKE-001  # zorunlu, run ID
related_tc: [TC-PRJ-005]           # zorunlu
external: "https://github.com/.../issues/1234"  # zorunlu
opened: 2026-05-22                 # zorunlu
closed: 2026-05-25                 # zorunlu (mirror sadece close sonrası)
fix_commit: a4b8c2d                # opsiyonel
reporter: "@username"              # zorunlu
---
```

### 3.6 Pre-condition (`shared/pre-conditions/PRE-*.md`)

```yaml
---
id: PRE-001
title: "Admin olarak login"
description: ""
setup_steps: ["..."]
teardown_steps: []                 # opsiyonel
---
```

### 3.7 Requirement (`requirements/REQ-*.md`)

```yaml
---
id: REQ-AUTH-001
title: ""
domain: AUTH
source: "internal-spec" | "customer-ticket" | "compliance" | "exploratory"
external: ""                       # opsiyonel: Jira/Linear/Notion link
covered_by: [TC-AUTH-001, TC-AUTH-002]  # otomatik üretilir
status: active                     # active | superseded | rejected
---
```

### 3.8 Milestone (`milestones/R-*.md`)

```yaml
---
id: R-2026.Q2
title: ""
target_date: 2026-06-30
status: planning                   # planning | in_progress | closed | cancelled
scope: ""
exit_criteria: ["..."]
plans: [TP-2026.Q2-RELEASE]
---
```

### 3.9 Exploratory Charter (`exploratory/EXP-*.md`)

```yaml
---
id: EXP-2026-05-22-llm-agent
title: ""
charter: ""                        # 1-2 cümle: ne arıyoruz
duration_minutes: 60               # zorunlu
testers: ["@username"]
date: 2026-05-22
findings: []                       # bug refs, observations
related_tc: []                     # bu session sonucu eklenen TC'ler
---
```

---

## 4. Status değerleri (enum)

### Result status
`pass` | `fail` | `blocked` | `skipped` | `untested` | `retest` | `not-applicable`

### TC status
`draft` | `active` | `deprecated`

### Automation status
`not-automated` | `in-progress` | `automated` | `out-of-scope`

### Priority
`P0` (blokçu) | `P1` (yüksek) | `P2` (orta) | `P3` (düşük)

### Severity
`S1` (kritik) | `S2` (büyük) | `S3` (orta) | `S4` (küçük)

### Type
`functional` | `smoke` | `regression` | `integration` | `api` | `ui` | `perf` | `security` | `a11y` | `exploratory`

---

## 5. Dosya naming

| Artifact | Dosya adı pattern | Örnek |
|---|---|---|
| Test Case | `{ID}-{kebab-case-slug}.md` | `TC-AUTH-001-basarili-login.md` |
| Pre-condition | `{ID}-{slug}.md` | `PRE-001-admin-login.md` |
| Shared Step | `{ID}-{slug}.md` | `SS-001-login-form-doldur.md` |
| Requirement | `{ID}-{slug}.md` | `REQ-AUTH-001-login-spec.md` |
| Test Plan | `{slug}.yml` | `2026.Q2-release.yml` |
| Test Run | `{ID}.yml` | `TR-2026-05-22-SMOKE-001.yml` |
| Defect | `{ID}.md` | `GH-1234.md` |
| Milestone | `{ID}.md` | `R-2026.Q2.md` |
| Exploratory | `{ID}.md` | `EXP-2026-05-22-llm-agent.md` |

Slug: küçük harf, ASCII, sadece `[a-z0-9-]`, max 50 karakter.

---

## 6. Otomasyon referansları

`automation.refs` listesindeki her yol şu kurallara uymalı:

1. **Repo köküne göre relative**. `e2e/bdd/features/auth/login.feature:12` ✓, `/Users/.../login.feature` ✗
2. **Line number opsiyonel**. `:12` belirli senaryoya işaret eder; yoksa tüm dosya kastedilir
3. **Dosya var olmalı**. `validate.mjs` bunu kontrol eder
4. **BDD feature'da `@TC-*` tag varsa eşleşmeli**. Tag yoksa warning, mismatch ise fail

### BDD ↔ TC eşlemesi

`.feature` dosyalarında scenario üzerine etiket:
```gherkin
@TC-AUTH-001
Scenario: Geçerli bilgilerle başarılı oturum açma
```

Pytest testlerinde marker veya docstring:
```python
@pytest.mark.tc("TC-AUTH-001")
def test_login_success():
    ...
```

Playwright spec'lerinde test başlığı:
```ts
test("TC-AUTH-001 — başarılı login", async ({ page }) => { ... })
```

`tools/trace.mjs` her üç pattern'i de okur.

---

## 7. Versiyonlama

- TC dosyaları git history ile versiyonlanır. Frontmatter'da `version` field'ı yoktur.
- Run YAML'lar `tc_commit` field'ı tutar → o anki TC versiyonunu işaret eder
- Geçmiş Run'a bakarken o commit'e checkout etmek o anki TC'yi gösterir

---

## 8. CODEOWNERS suite-bazlı

`qa/.github/CODEOWNERS` (PR 1'de stub):

```
qa/cases/auth/      @security-team
qa/cases/billing/   @finance-team
qa/plans/           @qa-leads
qa/strategy/        @qa-leads
```

Suite eklendiğinde CODEOWNERS güncellenir.

---

## 9. CI gate'leri

`tools/validate.mjs` PR'da çalışır, şunları kontrol eder:

| Kontrol | Severity |
|---|---|
| Frontmatter schema | ❌ Fail |
| ID benzersizliği | ❌ Fail |
| Domain prefix kayıtlı mı | ❌ Fail |
| `automation.refs` yolu var mı | ❌ Fail |
| `requirements`, `pre_conditions` referansları gerçek mi | ❌ Fail |
| BDD tag mismatch | ⚠️ Warn |
| Markdown lint | ⚠️ Warn |
| Yetim TC (hiçbir plan/run referansı yok) | ℹ️ Info |

---

## 10. Değişiklik politikası

Bu doküman değişikliği `qa/strategy/` sahipleri (CODEOWNERS) tarafından review edilmelidir. ID şeması, frontmatter zorunlu alanları veya status enum'ları değişirse `tools/validate.mjs` ve mevcut artifact'ler de güncellenmelidir.
