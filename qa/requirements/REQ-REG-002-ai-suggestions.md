---
id: REQ-REG-002
title: "AI destekli regresyon set önerisi ve toplu kabul"
domain: REG
source: internal-spec
external: ""
covered_by: [TC-REG-003, TC-REG-004]
status: active
---

# REQ-REG-002 — AI regresyon set önerisi

## Tanım

Geçmiş koşum verisi, kod değişiklik history'si ve bug pattern'lerinden AI yüksek-risk regresyon setleri önerir. Kullanıcı önerileri inceleyip toplu kabul eder.

## Kabul Kriterleri

- [ ] `POST /regression-sets/ai-suggest?based_on=last_release` → öneri listesi (en az 3)
- [ ] Öneri scope: hangi TC'ler dahil, gerekçe (risk skoru, son fail history)
- [ ] `POST /regression-sets/accept` ile toplu kabul (200 + created_set_ids)
- [ ] AI önerisi audit log'a düşer (prompt + response özeti + accepted/rejected)
- [ ] Cost rails: günlük max 10 öneri request (per project)

## Bağımlılık

- REQ-REG-001 (regression set CRUD)
- REQ-SCN-003 (AI generation infra)
