# qa/test-design — Test Tasarımı Master Index

> **Not**: Bu dokümanlar `docs/test-design/BGTS_*.md`'den taşındı (PR 2). Dosya isimleri sadeleştirildi; içerik aynı. "BGTS" terimi orijinal terminoloji olarak korundu — branding decision için ayrı PR.

**Platform:** Cortex AI Automation — Test Yönetimi, Sentetik Veri, AI Destekli Otomasyon

---

## Doküman Haritası

```
qa/test-design/
├── README.md                           ← Bu dosya
│
│   ── ANA TEST TASARIMI ──
├── overview.md                         ← Ana test tasarımı (75 senaryo, 17 iş kuralı)
├── overview.json                       ← Ana test tasarımı (JSON format)
│
│   ── GENİŞLETİLMİŞ TEST KATEGORİLERİ ──
├── e2e-ui.md                           ← E2E/UI test senaryoları (59 yeni)
├── security.md                         ← Güvenlik test senaryoları (33)
├── performance.md                      ← Performans/Yük testleri (28)
├── rbac-matrix.md                      ← RBAC yetkilendirme matrisi (180+)
├── api-contracts.md                    ← API kontrat testleri (45+)
├── cross-cutting.md                    ← Cross-cutting concerns (42)
├── advanced-scenarios.md               ← İleri seviye (84: concurrency, a11y, DI)
├── specialized.md                      ← Uzmanlaşmış (49: WebSocket, i18n, edge)
├── n8n-aichat.md                       ← n8n workflow + AI chat (24)
├── syndata-module.md                   ← Sentetik veri modülü (38)
├── engine-proxy-notification.md        ← Engine proxy + notification (25)
├── engine-module.md                    ← Flask Engine tüm blueprint'ler (66)
├── exploratory-uat.md                  ← Keşifsel test + UAT (32)
├── extended-traceability.md            ← Genişletilmiş traceability matrisi
│
│   ── OPERASYONEL REHBERLER ──
├── smoke-release-checklist.md          ← Smoke test + release go/no-go
├── test-data-guide.md                  ← Test verisi hazırlama rehberi
├── risk-findings.md                    ← 10 kritik risk bulgusu + aksiyon planı
├── bdd-step-map.md                     ← BDD step definitions eşleştirme
│
│   ── GHERKIN BDD DESIGN FEATURE'LARI (design-only, runner'a bağlı değil) ──
└── features/
    ├── approvals-and-imports.feature
    ├── bdd-generation.feature
    ├── execution-and-analytics.feature
    ├── flows-integrations-api-tests.feature
    ├── members-and-dashboard.feature
    ├── regression-sets.feature
    ├── requirements-coverage.feature
    └── schedules-and-test-data.feature
```

## qa/test-design ile diğer qa/ klasörlerinin ilişkisi

- `qa/test-design/` — **Düşük seviye tasarım dokümanları** (BGTS_* analizi sonrası üretilen tematik test kategori dokümanları). "Senaryo katalogları" gibi düşün.
- `qa/cases/` — **Bağımsız, koşulabilir TC'ler** (markdown frontmatter + adımlar). PR 3'te `docs/test-analysis/manual-test-scenarios.md` buraya parçalanacak.
- `qa/strategy/` — **Üst seviye strateji** (test stratejisi, traceability mimarisi, risk register, coverage stratejisi).

Bu dokümanlar `qa/cases/`'in **kaynağı**: bir senaryo `qa/test-design/security.md`'de listeliyse, `qa/cases/security/TC-SEC-*.md` olarak somutlaştırılır.

## features/ neden burada?

`docs/test-design/features/`'tan 11 feature dosyası vardı:
- **3 dosya** (authentication, project_management, scenario_management) → `backend/tests/bdd/features/`'ın TR/EN duplikatıydı, **silindi**
- **8 dosya** (burada) → design-only Gherkin, hiçbir runner'a bağlı değil. PR 3'te ilgili `qa/cases/{domain}/` altına bölünebilir (örn. `approvals-and-imports.feature` → `approvals/` + `imports/`).

Şimdilik toplu duruyor.
