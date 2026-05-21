# BGTS Raporlama Mimarisi

## 1. Genel Bakış

```
┌───────────────────────────────────────────────────────────────────────┐
│                     RAPORLAMA MİMARİSİ                                │
│                                                                       │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                │
│  │   Veri       │   │  İşleme     │   │  Sunum      │                │
│  │  Kaynakları  │──▶│  Katmanı    │──▶│  Katmanı    │                │
│  └─────────────┘   └─────────────┘   └─────────────┘                │
│                                                                       │
│  E2E Playwright      Aggregator        HTML Rapor                    │
│  Engine BDD           Analyzer         JSON Export                    │
│  Backend pytest       Trend Engine     Markdown Özet                  │
│  API Test Runs        Coverage Calc    Allure Dashboard               │
│  Manual Exec          Root-Cause       Yönetici Paneli                │
└───────────────────────────────────────────────────────────────────────┘
```

## 2. Rapor Katmanları

### Katman 1 — Veri Toplama (Data Collection)

| Kaynak | Teknoloji | Çıktı Formatı | Konum |
|--------|-----------|----------------|-------|
| E2E Testler | Playwright | JSON + trace | `e2e/test-results/` |
| BDD Testler | pytest-bdd + Allure | Allure JSON | `engine/allure-results/` |
| Backend Testler | pytest --cov | Coverage XML + JSON | `backend/htmlcov/` |
| Engine Reporter | Flask Reporter | HTML + JSON | `engine/reports/` |
| Manual Execution | TSPM UI | PostgreSQL (tspm_execution_results) | DB |
| API Test Runs | TSPM API Testing | PostgreSQL (tspm_api_test_runs) | DB |

### Katman 2 — İşleme ve Analiz (Processing)

| Modül | Sorumluluk |
|-------|------------|
| `ReportAggregator` | Tüm kaynaklardan veri toplama, normalizasyon |
| `CoverageCalculator` | Requirement-Scenario-Execution coverage hesaplama |
| `TrendAnalyzer` | Zaman serisi trend analizi, flaky test tespiti |
| `RootCauseAnalyzer` | Başarısız testler için kök neden sınıflandırma |
| `TraceabilityEngine` | Requirement → Test → Automation → Result zinciri |

### Katman 3 — Sunum (Presentation)

| Format | Hedef Kitle | Detay Seviyesi |
|--------|-------------|----------------|
| HTML Rapor | QA Ekibi, Geliştiriciler | Tam detay, adım adım |
| JSON Export | CI/CD, Entegrasyonlar | Makine okunabilir |
| Markdown Özet | Sprint Review, PR | Orta detay |
| Yönetici Paneli | Test Yöneticisi, PM | Özet metrikler |
| Allure Dashboard | QA Lideri | İnteraktif, trend |

## 3. Rapor Tipleri

### 3.1 Test Execution Raporu

Her test çalıştırması sonrası otomatik üretilir.

```
execution_report_<run_id>_<timestamp>/
├── report.html          # Görsel HTML rapor
├── report.json          # Makine okunabilir JSON
├── summary.md           # Markdown özet
├── screenshots/         # Başarısız testlerin ekran görüntüleri
├── traces/              # Playwright trace dosyaları
└── logs/                # Test logları
```

**JSON Yapısı:**

```json
{
  "report_id": "uuid",
  "execution_id": "uuid",
  "project_id": "uuid",
  "title": "Sprint 12 Regression Run",
  "environment": {
    "browser": "chromium",
    "base_url": "https://staging.example.com",
    "os": "linux",
    "node_version": "18.x",
    "python_version": "3.12"
  },
  "timing": {
    "started_at": "2026-04-03T10:00:00Z",
    "finished_at": "2026-04-03T10:15:32Z",
    "duration_seconds": 932
  },
  "summary": {
    "total": 48,
    "passed": 42,
    "failed": 4,
    "skipped": 2,
    "pass_rate": 87.5,
    "severity_breakdown": {
      "critical": { "total": 8, "passed": 7, "failed": 1 },
      "high": { "total": 15, "passed": 14, "failed": 1 },
      "medium": { "total": 20, "passed": 18, "failed": 2 },
      "low": { "total": 5, "passed": 3, "failed": 0, "skipped": 2 }
    }
  },
  "results": [
    {
      "test_id": "TC-001",
      "scenario_id": "uuid",
      "title": "Başarılı giriş yapılabilmeli",
      "status": "passed",
      "duration_ms": 2340,
      "steps": [...],
      "tags": ["smoke", "auth"],
      "requirement_ids": ["REQ-AUTH-001"]
    }
  ],
  "coverage": {
    "requirements_covered": 35,
    "requirements_total": 40,
    "coverage_percent": 87.5
  },
  "trends": {
    "previous_pass_rate": 85.0,
    "delta": 2.5,
    "direction": "improving"
  }
}
```

### 3.2 Coverage Raporu

Requirement bazlı kapsam analizi.

### 3.3 Traceability Raporu

Uçtan uca izlenebilirlik matrisi.

### 3.4 Root-Cause Analysis Raporu

Başarısız testler için kök neden analizi.

### 3.5 Yönetici Özet Raporu

Üst yönetim için tek sayfa özet.

## 4. Rapor Üretim Akışı

```
Test Execution Tamamlandı
         │
         ▼
┌─────────────────┐
│ ReportAggregator │──── Veri toplama (DB + dosya sistemi)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ CoverageCalc    │──── Requirement coverage hesaplama
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ TraceabilityEng │──── Requirement → TC → Auto → Result zinciri
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ RootCauseAnalyz │──── Failed testler için sınıflandırma
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ TrendAnalyzer   │──── Geçmiş çalıştırmalarla karşılaştırma
└────────┬────────┘
         │
    ┌────┴────────┬──────────┐
    ▼             ▼          ▼
 HTML           JSON      Markdown
 Rapor          Export    Özet
```

## 5. CI/CD Entegrasyonu

### GitHub Actions

```yaml
- name: Test Execution Report
  if: always()
  run: |
    python -m backend.app.domains.tspm.reporting generate \
      --execution-id ${{ env.EXECUTION_ID }} \
      --formats html,json,md \
      --output reports/
    
- name: Upload Reports
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: test-reports-${{ github.sha }}
    path: reports/
```

### Webhook Entegrasyonu

Rapor hazır olduğunda webhook ile bildirim:

```json
{
  "event": "report.generated",
  "report_id": "uuid",
  "execution_id": "uuid",
  "summary": {
    "total": 48,
    "passed": 42,
    "pass_rate": 87.5
  },
  "download_urls": {
    "html": "/api/v1/reports/uuid/html",
    "json": "/api/v1/reports/uuid/json",
    "md": "/api/v1/reports/uuid/md"
  }
}
```

## 6. Saklama ve Arşivleme

| Veri Tipi | Saklama Süresi | Depolama |
|-----------|---------------|----------|
| Execution sonuçları | Süresiz | PostgreSQL |
| HTML raporlar | 90 gün | Dosya sistemi / S3 |
| JSON raporlar | 180 gün | Dosya sistemi / S3 |
| Ekran görüntüleri | 30 gün | Dosya sistemi / S3 |
| Trace dosyaları | 14 gün | Dosya sistemi |
| Allure sonuçları | 30 gün | Dosya sistemi |
| Trend verileri | Süresiz | PostgreSQL |
