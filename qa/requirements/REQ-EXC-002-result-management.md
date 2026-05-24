---
id: REQ-EXC-002
title: "Test sonucu yönetimi (durum güncelleme, yeniden çalıştırma)"
domain: EXC
source: internal-spec
external: ""
covered_by: [TC-EXC-002, TC-EXC-003]
status: active
---

# REQ-EXC-002 — Test sonucu yönetimi

## Tanım

Tamamlanmış koşumların sonuçları manuel olarak güncellenebilir (örn. test ortamı sorunu yüzünden false-fail) ve önceki koşumlar tek tıkla yeniden çalıştırılabilir.

## Kabul Kriterleri

- [ ] `PATCH /executions/{run_id}/results/{tc_id}` ile status değiştirme (fail → pass after manual verify)
- [ ] Değişikliğin audit log'a düşmesi (kim, neden, ne zaman)
- [ ] `POST /executions/{run_id}/rerun` → mevcut config ile yeni run
- [ ] Rerun original run'a referans verir (`parent_run_id`)
- [ ] Manuel override sonrası flaky tag eklenir (öneri)

## Bağımlılık

- REQ-EXC-001 (run yaratılmış olmalı)
