# qa/reporting — Kalite ve Raporlama Yönetim Sistemi

> **Not**: PR 2'de `docs/quality/`'den taşındı. Dosya isimleri sadeleştirildi (01_, 02_ prefix'leri kaldırıldı). İçerik aynı.

Bu klasör, Cortex AI Automation'ın raporlama, kalite checklist ve şablon yapısını tanımlar.

## Doküman İndeksi

| Doküman | Açıklama |
|---------|----------|
| [architecture.md](architecture.md) | Katmanlı raporlama sistemi, veri kaynakları, rapor tipleri, CI/CD entegrasyonu |
| [quality-checklist.md](quality-checklist.md) | Sprint, PR, Release ve periyodik kontrol listeleri |

## Şablonlar (template'ler)

| Şablon | Kullanım |
|---|---|
| [exec-summary.template.md](exec-summary.template.md) | Üst yönetim için tek sayfa kalite raporu |
| [release-signoff.template.md](release-signoff.template.md) | Release sign-off checklist (PR 1'de yaratıldı) |
| [rca.template.md](rca.template.md) | Başarısız test kök neden sınıflandırma şablonu |

## İlgili dokümanlar (farklı klasörlerde)

| Konu | Konum |
|---|---|
| Coverage stratejisi (4 boyutlu) | [../strategy/coverage-strategy.md](../strategy/coverage-strategy.md) |
| Traceability mimarisi (Requirement → TC → Automation → Run) | [../strategy/traceability.md](../strategy/traceability.md) |
| Otomatik üretilen coverage çıktıları | [../coverage/](../coverage/) |

## Rapor Şablonları

| Dosya | Format | Kullanım |
|-------|--------|----------|
| `reports/templates/execution_report.html` | HTML | Görsel test execution raporu |
| `reports/templates/execution_report_schema.json` | JSON Schema | Makine okunabilir rapor formatı |
| `reports/templates/execution_summary.md` | Markdown | PR ve Sprint Review özeti |

## Backend Raporlama Servisi

`backend/app/domains/tspm/reporting.py` modülü aşağıdaki bileşenleri içerir:

| Bileşen | Sorumluluk |
|---------|------------|
| `ReportBuilder` | Test sonuçlarından rapor nesnesi oluşturma |
| `CoverageCalculator` | Requirement-Scenario-Execution coverage hesaplama |
| `TraceabilityEngine` | Requirement → TC → Automation → Result zinciri kurma |
| `RootCauseAnalyzer` | Hata mesajlarından kök neden sınıflandırma |
| `ReportRenderer` | HTML / JSON / Markdown formatında rapor üretme |
| `QualityScorecard` | 5 boyutlu kalite puanı hesaplama |
| `generate_report()` | Dosyaya rapor yazma convenience fonksiyonu |

### Kullanım Örneği

```python
from backend.app.domains.tspm.reporting import (
    ReportBuilder, TestResult, TestStatus, Severity,
    ReportRenderer, RootCauseAnalyzer, generate_report, ReportFormat,
)
from datetime import datetime, timezone

builder = ReportBuilder(
    project_id="project-uuid",
    execution_id="exec-uuid",
    title="Sprint 12 Regression",
)

builder.set_environment(browser="chromium", base_url="https://staging.example.com")
builder.set_timing(
    started_at=datetime(2026, 4, 3, 10, 0, tzinfo=timezone.utc),
    finished_at=datetime(2026, 4, 3, 10, 15, tzinfo=timezone.utc),
)

builder.add_result(TestResult(
    test_id="TC-001",
    title="Başarılı giriş yapılabilmeli",
    status=TestStatus.PASSED,
    duration_ms=2340,
    severity=Severity.CRITICAL,
    module="auth",
    tags=["smoke", "auth"],
    requirement_ids=["REQ-AUTH-001"],
))

report = builder.build()

# Farklı formatlarda çıktı
files = generate_report(report, "reports/output", [
    ReportFormat.HTML,
    ReportFormat.JSON,
    ReportFormat.MARKDOWN,
])
```

## Kalite Metrikleri Hedefleri

| Metrik | Kırmızı | Sarı | Yeşil |
|--------|---------|------|-------|
| Genel Pass Rate | < 75% | 75-85% | > 85% |
| P0 Pass Rate | < 90% | 90-95% | > 95% |
| Requirement Coverage | < 70% | 70-90% | > 90% |
| Automation Rate | < 40% | 40-70% | > 70% |
| Flaky Test Oranı | > 10% | 5-10% | < 5% |

## Mimari Genel Bakış

```
Veri Kaynakları          İşleme                Sunum
─────────────          ──────────            ──────────
Playwright E2E ───┐
pytest Backend ───┤    ReportBuilder        HTML Rapor
pytest-bdd BDD ───┼──► CoverageCalc    ──► JSON Export
TSPM Execution ───┤    TraceabilityEng     Markdown Özet
Manual Results ───┘    RootCauseAnalyzer   Yönetici Paneli
                       QualityScorecard    Allure Dashboard
```
