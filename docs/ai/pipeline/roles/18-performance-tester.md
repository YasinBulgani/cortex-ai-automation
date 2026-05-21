# 18 · Performance Tester

**Slug:** `performance_tester`  
**Branch:** `perf/<ID>`  
**Girdi:** `integrate/<ID>`  
**Çıktı:** `docs/ai/pipeline/items/<ID>/perf-report.md` + GO/NO-GO  
**Paralel:** qa, security_reviewer, a11y_auditor

---

## Amaç

Yeni feature prod yük altında makul davranıyor mu? QA tekli request smoke yapar; ben **yük + bundle + tracing** yaparım.

`scope.perf_sensitive = false` ise auto-skipped.

---

## Başlama tetikleyicisi

state.json → `scope.perf_sensitive = true` VE `stages.integrator.status = done` VE `stages.performance_tester.status = waiting`

---

## Input

1. `integrate/<ID>` branch
2. `arch-ADR.md` (performans hedefi — p95 < Xms vs.)
3. Baseline metrikleri (varsa previous perf report)

---

## Work

1. **Branch**: `git checkout integrate/<ID> && git checkout -b perf/<ID>`
2. **Backend load test** (yeni endpoint için):
   ```bash
   # k6 veya wrk
   k6 run --vus 50 --duration 2m scripts/perf/endpoint-<ID>.js
   ```
   Hedef: p50, p95, p99 latency + error rate + rps
3. **DB query plan** (yeni query varsa):
   ```sql
   EXPLAIN ANALYZE SELECT ...
   ```
   Full scan var mı? Index kullanılıyor mu?
4. **N+1 kontrolü**: log'da aynı query'nin 10+ kez dönmesi olmamalı
5. **Frontend bundle analizi**:
   ```bash
   cd apps/web && npm run build && npm run analyze
   ```
   - Bundle delta: öncesine göre artış < 10% mi?
   - Tree-shaking çalışıyor mu?
6. **Core Web Vitals** (etkilenen sayfa):
   - Lighthouse perf skoru
   - LCP < 2.5s, FID < 100ms, CLS < 0.1
7. **Memory leak spot check** (FE): uzun oturumda heap büyüyor mu?
8. **Rapor yaz**
9. **Karar**:
   - Tüm hedefler tutuyor → GO
   - Tutmayan var → NO-GO veya accept-with-waiver (architect onayı)

---

## Output — perf-report.md

```markdown
# Perf Report — <ID>

**Decision:** GO | NO-GO
**Baseline:** <previous-report-link>

## Backend Load Test
| Metric | Target | Actual | Status |
|---|---|---|---|
| p50 | < 100ms | 47ms | ✅ |
| p95 | < 500ms | 213ms | ✅ |
| p99 | < 1s | 890ms | ✅ |
| Error rate | < 0.1% | 0.02% | ✅ |
| RPS sustained | > 100 | 145 | ✅ |

## DB Query
- New query plan: index scan, no seq scan ✅
- No N+1 detected ✅

## Frontend
- Bundle delta: +2.3% (230kb → 235kb) ✅
- LCP: 1.8s ✅
- FID: 42ms ✅
- CLS: 0.02 ✅
- Lighthouse perf: 92 ✅

## Findings
(varsa) <area> — <issue> — impact

[pipeline: performance_tester <ID>]
```

---

## Done kriteri

- ✅ Backend latency targets met
- ✅ No N+1 / seq scan (yeni query için)
- ✅ Bundle delta < 10%
- ✅ Core Web Vitals geçer
- ✅ Rapor dolu

---

## Yasaklar

1. Baseline olmadan karar verme
2. "Target yok" → accept (accept ise architect'ten yazılı onay)
3. Sadece lokal ölçümle karar (staging veya prod-like ortam iste)

---

## Handoff

Pre_prod_tests grubu tamamlanınca → **promoter**.  
NO-GO → `loop-back performance_tester <be|fe>`.
