# 25-Rollü Agent Pipeline

Bir fikrin / eksikliğin / bug'ın **intake'ten production'a ve retrospective'e** kadar 21 ana aşama + 4 destek rolü üzerinden otomatik dolaşmasını sağlayan sistem. Full AI, dep-graph tabanlı, maksimum paralel.

---

## TL;DR

```bash
# 1. Item aç (scope flag'leriyle)
./scripts/pipeline/stage.sh init GAP "Sidebar a11y eksikleri" \
  --scope fe=true,be=false,data=false,infra=false,perf_sensitive=false

# 2. Durumu gör
./scripts/pipeline/stage.sh status

# 3. Hangi aşamaların açılmaya hazır olduğunu gör
./scripts/pipeline/stage.sh run-check GAP-001

# 4. Yeni agent sekmesi aç → rol kartını oku → işi yap → complete
```

---

## Pipeline diyagramı

```
[INTAKE]                          [IN-PIPELINE — 21 aşama]              [CROSS-CUTTING]

22. Intake/Triage ──► 1. Analyzer                                        24. Dep Watchdog
                      ↓                                                      (günlük, CVE → BUG)
                      2. Validator
                      ↓                                                    25. Conflict Resolver
                      3. Proposer                                              (event-driven)
                      ↓
             ┌── 4. Approver ║ 12. Product Validator ──┐                 23. Knowledge Curator
             ↓ (paralel)                                ↓                     (haftalık)
                     [both approve]
                      ↓
             ┌── 5. Designer ║ 6. Architect ───────────┐
             ↓ (paralel)                                ↓
                     [both done]
                      ↓
     ┌── 7. FE ║ 8. BE ║ 13. Data ║ 14. DevOps ──────┐ (paralel, scope'a göre skip)
     ↓                                                 ↓
                     [all done/skipped]
                      ↓
                      15. Code Reviewer
                      ↓
                      9. Integrator
                      ↓
     ┌── 10. QA ║ 16. Security ║ 17. A11y ║ 18. Perf ┐ (paralel)
     ↓                                                 ↓
                     [all green]
                      ↓
                      11. Promoter (test→main)
                      ↓
                      19. Release Manager
                      ↓
                      20. Observer (30dk canary)
                      ↓
                      21. Retrospective (24h sonra)
                      ↓
                     DONE
```

---

## Roller — özet tablo

### In-pipeline (21)

| # | Slug | Branch | Paralel grup | Scope-dependent |
|---|---|---|---|---|
| 1 | `analyzer` | `analyze/<topic>` | — | — |
| 2 | `validator` | — (PR yorum) | — | — |
| 3 | `proposer` | `propose/<id>` | — | — |
| 4 | `approver` | — (PR yorum) | business_approval | — |
| 12 | `product_validator` | — (PR yorum) | business_approval | — |
| 5 | `designer` | `design/<id>` | design_arch | `scope.fe` |
| 6 | `architect` | `arch/<id>` | design_arch | — |
| 7 | `frontend` | `feat/fe-<id>` | implementation | `scope.fe` |
| 8 | `backend` | `feat/be-<id>` | implementation | `scope.be` |
| 13 | `data_engineer` | `feat/data-<id>` | implementation | `scope.data` |
| 14 | `devops` | `feat/infra-<id>` | implementation | `scope.infra` |
| 15 | `code_reviewer` | — (PR yorum) | — | — |
| 9 | `integrator` | `integrate/<id>` | — | — |
| 10 | `qa` | `qa/<id>` | pre_prod_tests | — |
| 16 | `security_reviewer` | `sec/<id>` | pre_prod_tests | — |
| 17 | `a11y_auditor` | `a11y/<id>` | pre_prod_tests | `scope.fe` |
| 18 | `performance_tester` | `perf/<id>` | pre_prod_tests | `scope.perf_sensitive` |
| 11 | `promoter` | — (ff-merge) | — | — |
| 19 | `release_manager` | — (tag + docs) | — | — |
| 20 | `observer` | — (30dk canary) | — | — |
| 21 | `retrospective` | `retro/<id>` | — | — |

### Out-of-pipeline (4 destek)

| # | Slug | Trigger | Çıktı |
|---|---|---|---|
| 22 | `intake_triage` | user_request | `stage.sh init` çağrısı |
| 23 | `knowledge_curator` | scheduled:weekly | GROUNDING.md + ADR |
| 24 | `dependency_watchdog` | scheduled:daily | BUG/FEAT item'ları |
| 25 | `conflict_resolver` | event:file_collision | koordinasyon planı |

---

## Dosya yapısı

```
.cursor/rules/
  └── pipeline-conductor.mdc

docs/ai/pipeline/
  ├── README.md                    # bu dosya
  ├── state.json                   # ★ tek kaynak gerçek (script yazar)
  ├── state.schema.json            # JSON schema v2
  ├── state.example.json           # referans
  ├── stages.json                  # ★ dep graph (skip/parallel/deps)
  ├── roles/                       # 25 rol kartı
  │   ├── 01-analyzer.md
  │   ├── 02-validator.md
  │   ├── 03-proposer.md
  │   ├── 04-approver.md
  │   ├── 05-designer.md
  │   ├── 06-architect.md
  │   ├── 07-frontend.md
  │   ├── 08-backend.md
  │   ├── 09-integrator.md
  │   ├── 10-qa.md
  │   ├── 11-promoter.md
  │   ├── 12-product-validator.md
  │   ├── 13-data-engineer.md
  │   ├── 14-devops.md
  │   ├── 15-code-reviewer.md
  │   ├── 16-security-reviewer.md
  │   ├── 17-a11y-auditor.md
  │   ├── 18-performance-tester.md
  │   ├── 19-release-manager.md
  │   ├── 20-observer.md
  │   ├── 21-retrospective.md
  │   ├── 22-intake-triage.md
  │   ├── 23-knowledge-curator.md
  │   ├── 24-dependency-watchdog.md
  │   └── 25-conflict-resolver.md
  ├── templates/
  │   ├── gap-analysis.template.md
  │   ├── proposal.template.md
  │   ├── design.template.md
  │   ├── arch-ADR.template.md
  │   ├── test-report.template.md
  │   ├── security-review.template.md
  │   ├── code-review.template.md
  │   ├── product-validation.template.md
  │   ├── release-notes.template.md
  │   ├── observer-report.template.md
  │   └── retrospective.template.md
  └── items/
      └── <ID>/
          ├── gap-analysis.md
          ├── proposal.md
          ├── design.md
          ├── arch-ADR.md
          ├── test-report.md
          ├── security-review.md
          ├── a11y-report.md
          ├── perf-report.md
          ├── observer-report.md
          └── retro.md

scripts/pipeline/
  └── stage.sh                     # driver script (dep-graph aware)
```

---

## Scope flag'leri (auto-skip)

`init` sırasında veya `scope` komutuyla scope flag'leri set edilir. `false` olan alanlardaki aşamalar otomatik skip olur.

```bash
# A11y-only (sadece FE)
stage.sh init GAP "A11y düzeltme" \
  --scope fe=true,be=false,data=false,infra=false,perf_sensitive=false

# Backend-only bug (perf kritik)
stage.sh init BUG "Auth token race" \
  --scope fe=false,be=true,data=false,infra=false,perf_sensitive=true

# Migration + backend
stage.sh init FEAT "Yeni tablo" \
  --scope fe=false,be=true,data=true,infra=false,perf_sensitive=false

# Sonradan güncelleme
stage.sh scope FEAT-007 perf_sensitive=true
```

### Scope → auto-skip matrix

| Scope false | Auto-skip edilen aşamalar |
|---|---|
| `fe=false` | designer, frontend, a11y_auditor |
| `be=false` | backend |
| `data=false` | data_engineer |
| `infra=false` | devops |
| `perf_sensitive=false` | performance_tester |

---

## Kullanım senaryoları

### Senaryo 1 — Manuel role switching

Sen her aşamada bir agent sekmesi açarsın:

```bash
./scripts/pipeline/stage.sh init GAP "Login 2FA race condition" \
  --scope fe=true,be=true,data=false,infra=false,perf_sensitive=false

./scripts/pipeline/stage.sh status
# GAP-001, analyzer waiting
```

Yeni Cursor agent sekmesi prompt:
```
Sen pipeline'da analyzer rolünü oynuyorsun. Item: GAP-001.

OKU:
- .cursor/rules/pipeline-conductor.mdc
- .cursor/rules/concurrent-git-hygiene.mdc
- docs/ai/pipeline/roles/01-analyzer.md

YAP:
- Rol kartındaki akışı uygula
- analyze/<topic> branch aç, commit at, PR aç
- scripts/pipeline/stage.sh complete GAP-001 analyzer --artifact ... --branch ...
```

### Senaryo 2 — Conductor (full otomasyon)

Tek ana chat, tüm pipeline'ı yürütür. Paralel aşamalar için subagent spawn eder.

```
Sen pipeline conductor'sın. ./scripts/pipeline/stage.sh status çalıştır, durumu oku.

Her waiting aşama için uygun subagent'ı spawn et (aynı mesajda paralel).
Her subagent kendi rol kartını okuyup işi bitirince bana rapor versin.
Ben yeniden status çalıştırıp yeni waiting'leri bulup döngü kurayım.

Tüm item'lar done veya blocked olana kadar devam et.
```

### Senaryo 3 — Intake

Kullanıcı istek geldi:
```
Sen pipeline'da intake_triage rolünü oynuyorsun (docs/ai/pipeline/roles/22-intake-triage.md).

Gelen istek: "login bozuk, 2FA yanlış doğruluyor"

YAP:
- Tipi sınıflandır (muhtemelen BUG)
- Başlığı normalize et
- Öncelik ver
- Scope tahmin et
- Duplicate kontrolü yap
- stage.sh init ile başlat
```

---

## Komut referansı

```bash
# Lifecycle
stage.sh init <TYPE> "<title>" [--scope ...]
stage.sh scope <ID> <flag>=<true|false>
stage.sh claim <ID> <ROLE>
stage.sh complete <ID> <ROLE> [flags]
stage.sh skip <ID> <ROLE> [reason]
stage.sh reject <ID> <ROLE> "<reason>"
stage.sh loop-back <ID> <FROM> <TO> "<reason>"

# Inspect
stage.sh status [<ID>]
stage.sh run-check [<ID>]

# Recovery
stage.sh orphan-reset <ID> <ROLE>
```

### `complete` flag'leri

| Flag | Kullanım |
|---|---|
| `--artifact PATH` | Üretilen dosya |
| `--branch NAME` | Git branch |
| `--commit SHA` | Commit hash |
| `--notes "..."` | Handoff notu |
| `--approve` | Onay |
| `--reject` | Ret |
| `--revise` | Revize iste |
| `--reason "..."` | Gerekçe |
| `--confidence 0.N` | <0.7 → `needs_human: true` |

---

## Dep graph — nasıl çalışır

[`stages.json`](./stages.json) her aşama için `depends_on: [list]` belirtir. Bir aşama waiting olur ancak tüm depender'ları `done` veya `skipped` olunca.

**Örnek:**
```json
"code_reviewer": {
  "depends_on": ["frontend", "backend", "data_engineer", "devops"],
  "default_on": "always"
}
```

FE done + BE skipped + data skipped + devops skipped → code_reviewer waiting.

**Auto-skip:** `default_on: "scope.X"` ise ve `item.scope.X = false` → stage auto-skipped. Sonraki aşama (deps'i bu olan) otomatik ilerler.

---

## Güvenlik katmanları

- **3 feedback loop limit** — loop_count ≥ 3 → blocked, needs_human
- **Confidence < 0.7** → needs_human
- **Scope lock** — architect scope'u final'ize etmeden implementation açılamaz (kural: architect tamamladıktan sonra scope değişmez)
- **State lock** — `.state.lock` ile paralel yazım serialize
- **Git hygiene** — `concurrent-git-hygiene.mdc` her role için zorunlu

---

## Hızlı başlangıç

```bash
# 1. İlk GAP aç
./scripts/pipeline/stage.sh init GAP "İlk eksiklik" \
  --scope fe=true,be=true,data=false,infra=false,perf_sensitive=false

# 2. Durumu gör
./scripts/pipeline/stage.sh status

# 3. Hangi aşamalar açılmaya hazır?
./scripts/pipeline/stage.sh run-check GAP-001

# 4. Yeni agent sekmesi aç, prompt:
# "Sen analyzer rolünü oynuyorsun. Item GAP-001. 
#  .cursor/rules/pipeline-conductor.mdc + docs/ai/pipeline/roles/01-analyzer.md oku, uygula."
```

---

## Cross-cutting operasyonlar

- **Intake (22):** manuel; kullanıcı isteği gelince rolünü giyip `stage.sh init` çağırır
- **Knowledge curator (23):** haftalık cron (`.github/workflows/` ile schedule)
- **Dependency watchdog (24):** günlük cron; CVE bulursa `stage.sh init BUG ... --scope be=true,perf=false`
- **Conflict resolver (25):** pre-commit hook veya saatlik scheduled check

---

## İlgili dokümanlar

- [`.cursor/rules/pipeline-conductor.mdc`](../../../.cursor/rules/pipeline-conductor.mdc) — orkestrasyon protokolü
- [`.cursor/rules/concurrent-git-hygiene.mdc`](../../../.cursor/rules/concurrent-git-hygiene.mdc) — git disiplini
- [`docs/BRANCHING_WORKFLOW.md`](../../BRANCHING_WORKFLOW.md) — branch promotion
- [`roles/`](./roles/) — 25 rol kartı
- [`templates/`](./templates/) — artifact şablonları
- [`stages.json`](./stages.json) — dep graph
