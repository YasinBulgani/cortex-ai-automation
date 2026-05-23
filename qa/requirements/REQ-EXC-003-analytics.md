---
id: REQ-EXC-003
title: "Koşu analitikleri (trendler, flaky tespit)"
domain: EXC
source: internal-spec
external: ""
covered_by: [TC-EXC-004, TC-EXC-005]
status: active
---

# REQ-EXC-003 — Koşu analitikleri

## Tanım

Tarihsel run verisinden trendler (pass rate, duration) ve flaky test tespiti yapılır. Dashboard ve raporlama bu endpoint'leri tüketir.

## Kabul Kriterleri

- [ ] `GET /executions/trends?period=7d|30d|90d` → tarihsel pass rate, duration P95
- [ ] `GET /executions/flaky?min_runs=5&threshold=0.3` → flaky TC listesi
- [ ] Trend verileri cache (15 dk) — yüksek trafik
- [ ] Flaky tespit aynı algoritma: flip rate ≥ %30 (qa/tools/flakiness.mjs ile tutarlı)
- [ ] Quarantine entegrasyonu: flaky TC otomatik `e2e/quarantine.json`'a önerilir

## Bağımlılık

- REQ-EXC-001 (run history var olmalı)
