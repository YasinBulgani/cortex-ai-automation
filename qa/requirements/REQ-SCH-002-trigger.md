---
id: REQ-SCH-002
title: "Zamanlama tetikleme (manuel + otomatik)"
domain: SCH
source: internal-spec
external: ""
covered_by: [TC-SCH-002, TC-SCH-003]
status: active
---

# REQ-SCH-002 — Zamanlama tetikleme

## Tanım

Oluşturulan zamanlamalar cron tarafından otomatik tetiklenir ve UI'dan manuel tetiklenebilir. Boş zamanlama (senaryo bağlanmamış) tetiklenirse hata döner.

## Kabul Kriterleri

- [ ] `POST /schedules/{id}/trigger` → 200, async job başlatılır
- [ ] Cron otomatik tetikleme (5 dakikada bir tick)
- [ ] Tetiklenmiş job → execution_run oluşturur
- [ ] Boş zamanlama tetikleme → 400 "No scenarios bound to schedule"
- [ ] Aynı zamanlamanın paralel iki tetiklenmesi → ikinci 409 Conflict (lock)
- [ ] Cron history audit log'da görünür

## Bağımlılık

- REQ-SCH-001 (schedule var)
- REQ-EXC-001 (execution run yaratma)
- PRE-007 (engine + worker)
