---
id: REQ-SYN-002
title: "Sentetik veri üretimi ve dışa aktarma"
domain: SYN
source: internal-spec
external: ""
covered_by: [TC-SYN-002, TC-SYN-004]
status: active
---

# REQ-SYN-002 — Sentetik veri üretimi

## Tanım

Yüklenen kaynak veri setinden istatistiksel dağılımı koruyacak şekilde sentetik veri üretilir. PII anonimleştirilmiş, format ve constraints'ler korunur. Üretilen veri CSV/JSON/Parquet formatlarında dışa aktarılabilir.

## Kabul Kriterleri

- [ ] `POST /syndata/datasets/{id}/generate?count=1000` → asenkron job
- [ ] Üretim sırasında PII tespit edilmiş kolonlar maskelenir
- [ ] Sayısal kolonların distribution istatistikleri korunur (mean, stddev, percentile)
- [ ] Kategorik kolonların value distribution'ı korunur
- [ ] `GET /syndata/datasets/{id}/exports` formatları: csv, json, parquet
- [ ] Üretim audit log'a düşer (boyut, süre, anonimleştirme stratejisi)

## Bağımlılık

- REQ-SYN-001 (dataset yüklenmiş olmalı)
- REQ-SYN-003 (PII tespit tamamlanmış olmalı)
