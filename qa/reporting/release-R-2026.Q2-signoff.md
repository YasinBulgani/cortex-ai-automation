# Release Sign-off — R-2026.Q2

**Plan:** TP-2026.Q2-SMOKE-DAILY — Günlük smoke regression
**Tarih:** 2026-05-22
**Karar:** 🔴 **NO-GO**

---

## Test kapsamı

| | Sayı |
|---|---:|
| Plan kapsamındaki TC | 6 |
| Pass | 0 |
| Fail | 0 |
| Blocked | 0 |
| Skipped | 0 |
| **Hiç koşturulmadı** | 6 |
| Toplam koşum | 0 |

## Exit criteria

| Kriter | Durum | Detay |
|---|---|---|
| Tüm P0 pass | 🔴 FAIL | 0/6 P0 pass |
| Açık S1 defect = 0 | 🟢 PASS | 0 açık defect |

## Açık defect'ler

_Yok._

## Failed TC'ler

_Yok._

## Blocked TC'ler

_Yok._

## Hiç koşturulmamış TC'ler (6)

- TC-AUTH-001 (P0) — Geçerli kimlik bilgileri ile başarılı giriş
- TC-AUTH-002 (P0) — Hatalı parola ile giriş denemesi reddedilmeli
- TC-AUTH-003 (P0) — Sistemde olmayan e-posta ile giriş denemesi
- TC-AUTH-004 (P0) — Devre dışı bırakılmış hesap ile giriş engellenmeli
- TC-AUTH-005 (P0) — /me endpoint'i ile oturum sahibi bilgileri
- TC-AUTH-006 (P0) — Geçersiz token ile korumalı endpoint erişimi engellenmeli

## Önemli koşumlar (en son 5)

_Yok._

## Onaylar

- [ ] QA Lead
- [ ] Tech Lead
- [ ] PM

---

_Otomatik üretildi — `qa/tools/signoff.mjs` ile. Karar heuristic exit_criteria evaluation'ına dayanır; insan onayı zorunludur._
