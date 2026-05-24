# Performance Tests

Bu dizin **k6** (JavaScript) tabanlı load, stress, spike ve soak testleri içerir.

> **Not:** Önceden root `tests/load/` ve `tests/performance/` altındaydı.
> 2026-04 mimari temizliğinde buraya taşındı (ADR-0005).

## Yapı

```
performance-tests/
├── load/
│   └── api-load.js          # Genel API load testi
└── performance/
    ├── helpers/
    │   └── auth.js          # k6 için auth helper
    ├── load_test.js         # Sabit yük
    ├── soak_test.js         # Uzun süre dayanım
    ├── spike_test.js        # Ani yük artışı
    └── stress_test.js       # Kırılma noktası
```

## Kurulum

```bash
brew install k6           # macOS
# veya: https://k6.io/docs/get-started/installation/
```

## Çalıştırma

```bash
# API load testi
k6 run performance-tests/load/api-load.js

# Stress testi — kırılma noktasını bul
k6 run performance-tests/performance/stress_test.js

# 8 saatlik soak
k6 run --duration 8h performance-tests/performance/soak_test.js
```

## Ortam değişkenleri

Her test dosyası şu env'leri bekler:
- `BASE_URL` — hedef API (örn. `http://localhost:8000`)
- `API_TOKEN` — JWT token (helpers/auth.js bunu alır)
- `VUS` — virtual user sayısı (varsayılan her testte tanımlı)

## CI entegrasyonu

Bu testler **her PR'da çalışmaz** — pahalı. Nightly / release öncesi tetiklenir:

```yaml
# .github/workflows/performance.yml
on:
  schedule:
    - cron: '0 2 * * *'  # her gece 02:00
  workflow_dispatch:     # manuel tetikleme
```

## Raporlama

k6 JSON output → Prometheus/Grafana (`infra/grafana/`) veya k6 Cloud.

## İlgili

- [qa/strategy/test-strategy.md](../qa/strategy/test-strategy.md) — test taksonomisi
- [ADR-0005](../docs/adr/0005-test-taksonomisi.md) — test katmanları kararı
