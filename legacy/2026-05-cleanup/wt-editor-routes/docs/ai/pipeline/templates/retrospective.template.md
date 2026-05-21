# Retrospective — {{ID}}

> **By:** retrospective-{{agent_id}} on {{date}}  
> **Pipeline süresi:** {{TOTAL_DURATION}} (analyzer → observer)  
> **Tahmini efor:** {{EST_EFFORT}} | **Gerçek efor:** {{ACTUAL_EFFORT}}

---

## Stage Süre Haritası

| Stage | Start → End | Duration | Paralel? |
|---|---|---|---|
| analyzer | T0 → T+Xm | Xm | — |
| validator | → | | |
| proposer | → | | |
| approver | → | | ∥ product_validator |
| product_validator | → | | ∥ approver |
| designer | → | | ∥ architect |
| architect | → | | ∥ designer |
| frontend | → | | ∥ backend/data/devops |
| backend | → | | ∥ |
| code_reviewer | → | | |
| integrator | → | | |
| qa | → | | ∥ security/a11y/perf |
| security_reviewer | → | | ∥ |
| a11y_auditor | → | | ∥ |
| promoter | → | | |
| release_manager | → | | |
| observer | → | | |

**Bottleneck:** <en uzun süren aşama ve sebebi>

---

## Loop-back Analizi

| # | From | To | Sebep | Önlenebilir mi? |
|---|---|---|---|---|
| 1 | qa | frontend | E2E keyboard-nav | EVET — designer checklist eksikti |

**Toplam:** N loop-back | **Önlenebilir olanlar:** M

### Önlenebilir loop-back'lerden dersler
- ...

---

## Efor Tahmin Kalitesi

- Proposer tahmini: {{EST_EFFORT}}
- Gerçekleşen: {{ACTUAL_EFFORT}}
- Sapma sebebi: <varsa>

---

## Karar Kalitesi

| Karar | Confidence | Outcome | Kalite |
|---|---|---|---|
| Validator approve (0.92) | high | doğru | ✓ |
| Approver approve (0.88) | high | doğru | ✓ |
| Product validator approve (0.80) | medium | ? | follow-up'ta görülür |
| Observer HEALTHY (0.95) | high | doğru | ✓ |

---

## Scope Değişikliği

- Başlangıç scope: {{INITIAL_SCOPE}}
- Nihai scope: {{FINAL_SCOPE}}
- Scope creep oldu mu? <evet/hayır, detay>

---

## 3-3-3: Keep / Stop / Start

### Keep doing (işe yaradı)
- <...>
- <...>
- <...>

### Stop doing (çalışmadı)
- <...>
- <...>
- <...>

### Start doing (deneyelim)
- <yeni convention / process önerisi>
- <...>
- <...>

---

## Pattern Tespiti

<Önceki retrolarla karşılaştır — tekrar eden sorun/başarı var mı?>

- 3+ retroda benzer: <pattern> → ADR'ye dönüştürülmeli
- İlk kez gözlendi: <pattern> → izlemeye al

---

## GROUNDING.md Güncellemeleri

- [ ] <convention eklenecek>
- [ ] <anti-pattern eklenecek>
- [ ] <eskimiş madde silinecek>

---

## Follow-up Items

- [ ] GAP/FEAT açılacak: <başlık>
- [ ] ADR yazılacak: <konu>
- [ ] Template iyileştirilecek: <hangi>

---

[pipeline: retrospective {{ID}}]
