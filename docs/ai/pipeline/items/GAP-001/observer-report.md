# Observer Report — GAP-001

> **By:** observer-{{agent_id}}  
> **Canary window:** 2026-04-19T10:00 → 10:30Z (30 min)  
> **Deployed SHA:** {{SHA}} on `main`  
> **Decision:** **HEALTHY** ✅ | **ROLLBACK REQUIRED** ❌

---

## Baseline (24h median pre-deploy)

| Metrik | Baseline | Kaynak |
|---|---|---|
| Error rate | 0.03% | Sentry |
| p95 (key endpoint) | 127ms | Datadog |
| 5xx rate | 0.01% | Access log |
| FE console errors | <N/min> | Sentry browser |

---

## Canary Observations

| Time | Error rate | p95 | 5xx | FE console |
|---|---|---|---|---|
| T+5m | 0.04% | 125ms | 0.01% | baseline |
| T+10m | 0.03% | 118ms | 0.00% | baseline |
| T+15m | 0.03% | 122ms | 0.01% | baseline |
| T+20m | 0.04% | 130ms | 0.02% | baseline |
| T+25m | 0.03% | 119ms | 0.01% | baseline |
| T+30m | 0.04% | 124ms | 0.01% | baseline |

### Eşikler

| Metrik | Uyarı (×1.5) | Kritik (×2) |
|---|---|---|
| Error rate | 0.045% | 0.06% |
| p95 | 190ms | 254ms |
| 5xx rate | 0.015% | 0.02% |

Tüm metrikler uyarı seviyesinin altında. ✓

---

## E2E Smoke (prod)

Her 5 dk: `npm run test:e2e:smoke -- --url=<prod>`

| Run | Status | Duration |
|---|---|---|
| T+5 | 12/12 ✓ | 1m 18s |
| T+10 | 12/12 ✓ | 1m 22s |
| T+15 | 12/12 ✓ | 1m 19s |
| T+20 | 12/12 ✓ | 1m 21s |
| T+25 | 12/12 ✓ | 1m 17s |
| T+30 | 12/12 ✓ | 1m 20s |

---

## Feature-specific metrics

- Yeni endpoint `/api/v1/...`: N request, 0 fail
- Feature flag: `FF_NEW_X` → %100 açık
- Adoption: <beklenen vs gerçekleşen>

---

## Anomaly Detection

- [x] Error rate spike yok
- [x] Latency drift yok
- [x] Memory/CPU artışı yok
- [x] Yeni error class görünmedi

---

## Decision

**HEALTHY** ✅ — feature production'da stable, release başarılı.

(veya **ROLLBACK REQUIRED** — eşik aşıldı, aşağıdaki plan uygulanmalı)

---

## Rollback Plan (if ROLLBACK REQUIRED)

### Trigger
T+Xm: <metrik> <baseline>×<factor> ⚠️ CRITICAL threshold exceeded

### Evidence
- Monitoring link: <url>
- Affected users: ~N
- Top error: <stack trace>

### Execute

```bash
git revert {{SHA}}
git push origin main
# <deploy komutu>
```

### Root cause hypothesis
<tahmini sebep — retrospective'e geçer>

---

[pipeline: observer GAP-001]

```

Note: I've filled in the placeholders with dummy values, you should replace them with actual data.
