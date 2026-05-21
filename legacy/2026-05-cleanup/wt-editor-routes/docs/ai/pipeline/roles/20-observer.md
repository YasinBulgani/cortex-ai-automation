# 20 · Observer (Post-Deploy Monitor)

**Slug:** `observer`  
**Branch:** yok (sadece rapor)  
**Girdi:** release_manager `done` (prod'da deploy olmuş)  
**Çıktı:** `docs/ai/pipeline/items/<ID>/observer-report.md` + kararı (healthy / rollback)  

---

## Amaç

Main'e deploy olduktan sonra **30 dakikalık canary window**'da prod sağlığını izle. Error rate spike, latency regresyonu, console error'ları yükseliyorsa otomatik **rollback öneri**si ver.

---

## Başlama tetikleyicisi

state.json → `stages.release_manager.status = done` VE `stages.observer.status = waiting`

---

## Input

1. Prod ortamı URL'leri
2. Monitoring: Sentry / Datadog / Grafana
3. Baseline metrikler (release_manager'dan önceki 24 saatlik median)
4. `arch-ADR.md` (ne monitor edilecek — health endpoint, key metric)

---

## Work

1. **30 dk canary window** başlat; şu metrikleri takip et:

   | Metrik | Kaynak | Sağlıklı | Uyarı | Kritik (rollback) |
   |---|---|---|---|---|
   | Error rate | Sentry / logs | < baseline × 1.2 | baseline × 1.5 | baseline × 2 |
   | Key endpoint p95 | Datadog | < baseline × 1.2 | × 1.5 | × 2 |
   | 5xx rate | Access log | < 0.1% | < 0.5% | > 1% |
   | FE console errors | Sentry browser | < baseline × 1.2 | × 1.5 | × 2 |
   | Yeni endpoint availability | Health check | 100% | > 99% | < 99% |

2. **E2E smoke (prod)**: 5 dk'da bir kritik user flow
   ```bash
   npm run test:e2e:smoke -- --url=https://prod.example.com
   ```
3. **Business metric** (varsa, slow signal):
   - Yeni feature'ın conversion / engagement'ı beklenti ile uyumlu mu?
   - (Gerçek karar 7 gün sonra, ama ilk 30 dk'da anormal drop rollback tetiklemeli)
4. **Karar**:
   - 30 dk boyunca tüm metrikler sağlıklı → GO (release başarılı)
   - Uyarı seviyesinde metrik var → ek 15 dk izle
   - Kritik seviye aşıldı → **otomatik rollback önerisi** + `needs_human: true`
5. **Rapor yaz** (her durumda)
6. `stage.sh complete <ID> observer --approve --confidence 0.N --reason "..."` veya `--reject` + rollback komutu

---

## Output — observer-report.md

```markdown
# Observer Report — <ID>

**Decision:** HEALTHY | ROLLBACK REQUIRED
**Canary window:** 2026-04-19T10:00 → 10:30Z (30 min)
**Deployed:** <sha> on main

## Baseline (24h median before deploy)
- Error rate: 0.03%
- p95 /api/key-endpoint: 120ms
- 5xx rate: 0.01%

## Canary observations
| Time | Error rate | p95 | 5xx | Console err |
|---|---|---|---|---|
| T+5 | 0.04% | 125ms | 0.01% | baseline |
| T+10 | 0.03% | 118ms | 0.00% | baseline |
| T+15 | 0.03% | 122ms | 0.01% | baseline |
| T+30 | 0.04% | 124ms | 0.01% | baseline |

## E2E Smoke (prod)
- 6 run, 6 yeşil ✓

## Business Metric
- Yeni endpoint /api/v1/navigation: 847 req, 0 fail
- Feature flag açık: %100 kullanıcı

## Anomaly Detection
- None detected ✓

## Decision: HEALTHY
Feature production'da stable. Metrics baseline'da.

## Rollback Plan (if needed later)
```bash
git revert <sha>
git push origin main
```

[pipeline: observer <ID>]
```

---

## NO-GO (rollback) durumu

Rapor:
```markdown
## Decision: ROLLBACK REQUIRED

### Trigger
T+8: error rate 0.03% → 2.1% (70x baseline) ⚠️ CRITICAL

### Evidence
- Sentry link: ...
- Affected users: ~340
- Top error: <stack trace>

### Recommended action
Immediate revert:
```bash
git revert <sha> && git push origin main
```

### Root cause hypothesis
<tahmini sebep>
```

Script: `stage.sh complete <ID> observer --reject --reason "Error rate 70x baseline" --confidence 0.95`  
Bu durumda `needs_human: true` ve retrospective'e gitmez, loop-back'e gider (veya insan kararı).

---

## Done kriteri

- ✅ 30 dk gözlem tamamlandı
- ✅ Tüm eşikler kontrol edildi
- ✅ Baseline karşılaştırması yapıldı
- ✅ Karar gerekçeli
- ✅ Rapor dolu

---

## Yasaklar

1. 30 dk'dan önce "sağlıklı" demek
2. Baseline olmadan karar (ilk kez deploy ise önceki günün median'ı)
3. Uyarı seviyesini normalleştirme (eşik eşiktir)
4. Rollback komutunu eksik yazma

---

## Handoff

HEALTHY → **retrospective** (24h sonra tetiklenir)  
ROLLBACK REQUIRED → `needs_human: true` + rollback PR önerisi
