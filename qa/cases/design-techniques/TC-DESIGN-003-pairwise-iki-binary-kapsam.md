---
id: TC-DESIGN-003
title: "Pairwise: 2×2 parametreli tüm ikili kapsamı doğrulama"
suite: design-techniques
priority: P2
type: [functional, regression]
status: active
owner: "@unassigned"
created: 2026-06-08
updated: 2026-06-08
automation:
  status: automated
  refs:
    - backend/tests/unit/test_design_service_helpers.py::TestFallbackPairwise::test_two_binary_params_cover_four_pairs
requirements: [REQ-DESIGN-002]
pre_conditions: []
tags: [design, pairwise, unit-test, coverage]
---

# TC-DESIGN-003 — Pairwise: 2×2 parametreli tüm ikili kapsamı doğrulama

## Önkoşul

Python ortamı hazır, backend unit test suite çalışır

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `pytest tests/unit/test_design_service_helpers.py::TestFallbackPairwise` çalıştır | Tüm testler yeşil |
| 2 | `test_two_binary_params_cover_four_pairs` testini özellikle kontrol et | 2 enum parametresi (a1/a2 × b1/b2) için tüm 4 kombinasyon üretilir |
| 3 | `test_safety_cap_200` testini kontrol et | 8 parametre × 6 değer → max 200 satır |
| 4 | `test_bool_fields_use_true_false` testini kontrol et | Bool parametreler True/False değerleri içerir |

## Ek Notlar

- 2 binary parametre için pairwise = tam kartezyen çarpım (4 kombinasyon) — azaltma yoktur
- Greedy algoritma: her senaryo oluşturulurken "look-ahead" puanlama ile en çok çift kapayan değer seçilir
- Güvenlik limiti: 200. satırdan önce break (>= 200, önceki bug'da > 200 yanlıştı)

---
_Section: Design Techniques — Pairwise unit test coverage._
