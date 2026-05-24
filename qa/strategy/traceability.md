# BGTS Traceability (İzlenebilirlik) Yapısı

## 1. Traceability Zinciri

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  REQUIREMENT │────▶│  TEST CASE   │────▶│  AUTOMATION  │────▶│  EXECUTION   │
│  (Gereksinim)│     │  (Manuel TC) │     │  (Otomasyon) │     │  (Sonuç)     │
│              │     │              │     │              │     │              │
│  REQ-AUTH-001│     │  TC-001      │     │  login.spec  │     │  PASSED      │
│  "Kullanıcı  │     │  "Başarılı   │     │  .ts:24      │     │  2340ms      │
│   giriş"     │     │   giriş"     │     │              │     │  03.04.2026  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │                    │
       │                    │                    │                    │
       ▼                    ▼                    ▼                    ▼
  tspm_requirements   tspm_scenarios    e2e/*.spec.ts         tspm_execution
  (PostgreSQL)        (PostgreSQL)      engine/tests/         _results (DB)
                      + tspm_scenario   features/*.feature
                      _requirements
```

## 2. Veritabanı İlişki Modeli

```sql
-- Mevcut tablolar ve ilişkiler

tspm_requirements (id, external_id, title, priority, project_id)
       │
       │ tspm_scenario_requirements (scenario_id, requirement_id)
       │
       ▼
tspm_scenarios (id, title, status, steps, project_id)
       │
       │ tspm_execution_results (scenario_id, execution_id, status)
       │
       ▼
tspm_executions (id, name, status, project_id)
       │
       │ tspm_execution_metrics (execution_id, total, passed, failed, pass_rate)
       │
       ▼
tspm_execution_metrics (id, total, passed, failed, pass_rate, duration_seconds)
```

### Otomasyon Bağlama Tablosu (Yeni)

Mevcut modellere otomasyon eşleme bilgisi eklemek için önerilen yapı:

```sql
CREATE TABLE tspm_scenario_automations (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id   UUID NOT NULL REFERENCES tspm_scenarios(id) ON DELETE CASCADE,
    automation_type VARCHAR(32) NOT NULL DEFAULT 'e2e',
        -- 'e2e', 'api', 'bdd', 'unit', 'integration'
    file_path     VARCHAR(500) NOT NULL,
        -- 'e2e/login.spec.ts'
    test_name     VARCHAR(500),
        -- 'başarılı giriş yapılabilmeli'
    line_number   INTEGER,
    framework     VARCHAR(32) DEFAULT 'playwright',
        -- 'playwright', 'pytest', 'pytest-bdd'
    last_sync_at  TIMESTAMPTZ DEFAULT NOW(),
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scenario_automations_scenario
    ON tspm_scenario_automations(scenario_id);
```

## 3. Tam Traceability Matrisi

### Örnek Zincir: Authentication Modülü

```
REQ-AUTH-001: Kullanıcı Girişi
├── TC-001: Geçerli email/parola ile giriş
│   ├── AUTOMATION: e2e/login.spec.ts → "başarılı giriş"
│   │   └── EXECUTION: Run #42 → PASSED (2340ms) — 03.04.2026
│   │   └── EXECUTION: Run #41 → PASSED (2100ms) — 02.04.2026
│   └── AUTOMATION: engine/tests/test_login.py → "test_valid_login"
│       └── EXECUTION: Run #42 → PASSED (120ms)
│
├── TC-002: Hatalı parola ile giriş reddi
│   ├── AUTOMATION: e2e/login.spec.ts → "hatalı parola red"
│   │   └── EXECUTION: Run #42 → PASSED (1800ms)
│   └── AUTOMATION: backend/tests/test_auth.py → "test_invalid_password"
│       └── EXECUTION: Run #42 → PASSED (45ms)
│
└── TC-003: Boş form gönderimi engeli
    └── AUTOMATION: e2e/login.spec.ts → "boş form engeli"
        └── EXECUTION: Run #42 → PASSED (1200ms)

REQ-AUTH-002: JWT Token Yenileme
├── TC-004: Token refresh endpoint
│   └── AUTOMATION: backend/tests/test_auth.py → "test_token_refresh"
│       └── EXECUTION: Run #42 → PASSED (30ms)
│
└── TC-005: Expired token 401 dönmeli
    └── AUTOMATION: backend/tests/test_auth.py → "test_expired_token"
        └── EXECUTION: Run #42 → PASSED (25ms)

REQ-AUTH-003: Oturum Zaman Aşımı
└── TC-006: 30 dk inaktivite sonrası logout
    └── AUTOMATION: ❌ YOK — Backlog'da (Sprint+1)
```

### Örnek Zincir: Senaryo Yönetimi

```
REQ-SCN-001: Senaryo CRUD
├── TC-020: Yeni senaryo oluşturma
│   ├── AUTOMATION: e2e/scenarios.spec.ts → "yeni senaryo oluşturulabilmeli"
│   │   └── EXECUTION: Run #42 → PASSED (4200ms)
│   └── AUTOMATION: backend/tests/test_tspm.py → "test_create_scenario"
│       └── EXECUTION: Run #42 → PASSED (80ms)
│
├── TC-021: Senaryo düzenleme
│   └── AUTOMATION: e2e/scenarios.spec.ts → "senaryo düzenlenebilmeli"
│       └── EXECUTION: Run #42 → PASSED (3800ms)
│
├── TC-022: Senaryo arama
│   └── AUTOMATION: e2e/scenarios.spec.ts → "senaryo aranabilmeli"
│       └── EXECUTION: Run #42 → FAILED (5200ms)
│           └── ROOT CAUSE: Timeout — arama indexi yavaş (>5s)
│
└── TC-023: Toplu silme
    └── AUTOMATION: e2e/scenarios.spec.ts → "toplu silme yapılabilmeli"
        └── EXECUTION: Run #42 → PASSED (6100ms)
```

## 4. Traceability Veri Modeli (JSON)

```json
{
  "traceability_matrix": {
    "generated_at": "2026-04-03T12:00:00Z",
    "project_id": "uuid",
    "chains": [
      {
        "requirement": {
          "id": "uuid",
          "external_id": "REQ-AUTH-001",
          "title": "Kullanıcı girişi",
          "priority": "critical",
          "source": "PRD v2.1"
        },
        "test_cases": [
          {
            "id": "uuid",
            "code": "TC-001",
            "title": "Geçerli email/parola ile giriş",
            "type": "functional",
            "status": "approved",
            "automations": [
              {
                "id": "uuid",
                "type": "e2e",
                "framework": "playwright",
                "file": "e2e/login.spec.ts",
                "test_name": "başarılı giriş yapılabilmeli",
                "line": 24,
                "executions": [
                  {
                    "execution_id": "uuid",
                    "run_name": "Sprint 12 Regression #42",
                    "status": "passed",
                    "duration_ms": 2340,
                    "executed_at": "2026-04-03T10:02:15Z",
                    "environment": "staging"
                  }
                ]
              }
            ]
          }
        ],
        "coverage_status": "fully_covered",
        "automation_status": "automated",
        "last_execution_status": "passed"
      }
    ],
    "summary": {
      "total_requirements": 14,
      "fully_covered": 8,
      "partially_covered": 4,
      "not_covered": 2,
      "automated": 9,
      "not_automated": 5,
      "last_run_passed": 8,
      "last_run_failed": 1
    }
  }
}
```

## 5. Bidirectional Traceability

### İleri İzleme (Forward): Requirement → Sonuç

Bir gereksinim hangi testlerle doğrulanıyor?

```
REQ-EXEC-001 "Test Çalıştırma"
  → TC-030 "Execution başlatma"
    → e2e/executions.spec.ts
      → Run #42: FAILED ⚠️
```

### Geri İzleme (Backward): Başarısız Test → Gereksinim

Başarısız bir test hangi gereksinimleri etkiliyor?

```
FAILED: e2e/executions.spec.ts → "execution tamamlanmalı"
  → TC-030 "Execution başlatma"
    → REQ-EXEC-001 "Test Çalıştırma" (Priority: CRITICAL) ⚠️
    → REQ-RPT-001 "Rapor üretimi" (Priority: HIGH) ⚠️
```

### Etki Analizi (Impact Analysis)

Bir gereksinim değiştiğinde hangi testler etkilenir?

```
DEĞİŞEN: REQ-AUTH-001 "Kullanıcı girişi" → MFA eklendi
  ETKİLENEN TESTLER:
  ├── TC-001 → GÜNCELLENMELI (MFA adımı ekle)
  ├── TC-002 → GÜNCELLENMELI (MFA hata senaryosu)
  ├── TC-003 → Değişiklik yok
  ├── e2e/login.spec.ts → GÜNCELLENMELI (4 test)
  └── backend/tests/test_auth.py → GÜNCELLENMELI (2 test)
  
  TAHMİNİ EFOR: 8 saat
  RİSK: YÜKSEK (Authentication modülü kritik)
```

## 6. Otomatik Traceability Senkronizasyonu

### Senaryo-Otomasyon Eşleme Kuralları

1. **Tag bazlı eşleme:** Playwright test'lerinde `@req:REQ-AUTH-001` tag kullanımı
2. **ID bazlı eşleme:** Test açıklamalarında `[TC-001]` referansı
3. **İsim bazlı eşleme:** Fuzzy matching ile senaryo başlığı-test adı eşleme

```typescript
// e2e/login.spec.ts — Önerilen tag yapısı
test("başarılı giriş yapılabilmeli @req:REQ-AUTH-001 @tc:TC-001", async ({ page }) => {
  // ...
});
```

```python
# engine/tests — Önerilen marker yapısı
@pytest.mark.requirement("REQ-AUTH-001")
@pytest.mark.testcase("TC-001")
def test_valid_login():
    pass
```

### Sync Komutu

```bash
python -m backend.app.domains.tspm.reporting sync-traceability \
  --project-id <uuid> \
  --e2e-dir e2e/ \
  --engine-test-dir engine/tests/ \
  --backend-test-dir backend/tests/
```

## 7. Traceability Dashboard Metrikleri

| Metrik | Formül | Hedef |
|--------|--------|-------|
| Requirement Coverage | Kapsanan REQ / Toplam REQ | >= 90% |
| Test Case Effectiveness | (PASS TC / Toplam TC) * 100 | >= 85% |
| Automation Rate | Otomatik TC / Toplam TC | >= 70% |
| Orphan Tests | TC'si olmayan otomasyon testi | 0 |
| Untraceable Requirements | TC'si olmayan gereksinim | 0 |
| Average Defect Leakage | Prod'a kaçan bug / Toplam bug | < 5% |
