# BGTS Coverage Matrisi

## 1. Coverage Boyutları

Platform 4 boyutlu coverage takibi sunar:

```
┌──────────────────────────────────────────────────────────────────┐
│                   COVERAGE MATRİSİ 4 BOYUT                       │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Requirement  │  │  Feature     │  │  Risk-Based  │          │
│  │  Coverage    │  │  Coverage    │  │  Coverage    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                    │
│         └────────────┬────┴────────────────┘                    │
│                      ▼                                          │
│              ┌──────────────┐                                   │
│              │  Automation  │                                   │
│              │  Coverage    │                                   │
│              └──────────────┘                                   │
└──────────────────────────────────────────────────────────────────┘
```

## 2. Requirement Coverage Matrisi

### Yapı

| Requirement ID | Başlık | Öncelik | Manuel TC | Otomasyon TC | Son Sonuç | Durum |
|---------------|--------|---------|-----------|-------------|-----------|-------|
| REQ-AUTH-001 | Kullanıcı girişi | P0-Critical | TC-001, TC-002 | e2e/login.spec.ts | PASSED | Kapsanıyor |
| REQ-AUTH-002 | JWT token yenileme | P0-Critical | TC-003 | e2e/login.spec.ts | PASSED | Kapsanıyor |
| REQ-AUTH-003 | Oturum zaman aşımı | P1-High | TC-004 | -- | N/A | Otomasyon Yok |
| REQ-PROJ-001 | Proje oluşturma | P0-Critical | TC-010, TC-011 | e2e/projects.spec.ts | PASSED | Kapsanıyor |
| REQ-PROJ-002 | Proje arşivleme | P2-Medium | TC-012 | -- | N/A | Otomasyon Yok |
| REQ-SCN-001 | Senaryo CRUD | P0-Critical | TC-020..TC-025 | e2e/scenarios.spec.ts | PASSED | Kapsanıyor |
| REQ-SCN-002 | Senaryo versiyonlama | P1-High | TC-026 | -- | N/A | Otomasyon Yok |
| REQ-EXEC-001 | Test çalıştırma | P0-Critical | TC-030..TC-033 | e2e/executions.spec.ts | FAILED | Risk |
| REQ-FLOW-001 | Akış editörü | P1-High | TC-040..TC-042 | e2e/flows.spec.ts | PASSED | Kapsanıyor |
| REQ-REG-001 | Regresyon seti | P1-High | TC-050, TC-051 | e2e/regression.spec.ts | PASSED | Kapsanıyor |
| REQ-APP-001 | Onay kuyruğu | P1-High | TC-060..TC-063 | e2e/approvals.spec.ts | PASSED | Kapsanıyor |
| REQ-IMP-001 | Dosya içe aktarma | P1-High | TC-070, TC-071 | e2e/import.spec.ts | PASSED | Kapsanıyor |
| REQ-COV-001 | Kapsam matrisi | P2-Medium | TC-080 | -- | N/A | Otomasyon Yok |
| REQ-RPT-001 | Rapor üretimi | P1-High | TC-090 | -- | N/A | Kapsanmıyor |

### Durum Tanımları

| Durum | Renk | Anlam |
|-------|------|-------|
| Kapsanıyor | Yesil | Manuel TC + Otomasyon + Son Execution PASSED |
| Otomasyon Yok | Sari | Manuel TC var, otomasyon bekleniyor |
| Risk | Kirmizi | Otomasyon var ama son execution FAILED |
| Kapsanmıyor | Gri | Ne manuel ne otomasyon TC tanımlanmış |

### Coverage Metrikleri

```
Toplam Gereksinim:         14
Kapsanan (Manuel TC var):  12  (85.7%)
Otomasyon Kapsama:          9  (64.3%)
Son Run Başarılı:           8  (57.1%)
Boşluk (Gap):               2  (14.3%)
Risk (Failed):               1  ( 7.1%)
```

## 3. Feature Coverage Matrisi

### Modül Bazlı Kapsam

| Modül | Toplam Özellik | Manuel TC | Otomasyon | Coverage % |
|-------|---------------|-----------|-----------|------------|
| Authentication | 5 | 5 | 4 | 80% |
| Projeler | 4 | 4 | 3 | 75% |
| Senaryolar | 8 | 7 | 5 | 62.5% |
| Execution | 5 | 4 | 3 | 60% |
| Akışlar | 4 | 3 | 2 | 50% |
| Regresyon | 3 | 3 | 2 | 66.7% |
| Onaylar | 3 | 3 | 2 | 66.7% |
| İçe Aktarma | 3 | 2 | 1 | 33.3% |
| Coverage/Raporlama | 4 | 1 | 0 | 0% |
| API Testing | 5 | 2 | 0 | 0% |
| Integrations | 3 | 1 | 0 | 0% |
| **TOPLAM** | **47** | **35** | **22** | **46.8%** |

## 4. Automation Coverage Matrisi

### Manuel-Otomasyon Eşleme

| Manuel Senaryo | Otomasyon Dosyası | Eşleme Durumu | Öncelik |
|---------------|-------------------|---------------|---------|
| TC-001: Başarılı giriş | `e2e/login.spec.ts` → "başarılı giriş" | Eşlendi | P0 |
| TC-002: Hatalı giriş | `e2e/login.spec.ts` → "hatalı giriş" | Eşlendi | P0 |
| TC-010: Proje oluştur | `e2e/projects.spec.ts` → "proje oluşturulabilmeli" | Eşlendi | P0 |
| TC-020: Senaryo oluştur | `e2e/scenarios.spec.ts` → "yeni senaryo oluşturulabilmeli" | Eşlendi | P0 |
| TC-021: Senaryo düzenle | `e2e/scenarios.spec.ts` → "senaryo düzenlenebilmeli" | Eşlendi | P0 |
| TC-022: Senaryo ara | `e2e/scenarios.spec.ts` → "senaryo aranabilmeli" | Eşlendi | P1 |
| TC-023: Toplu silme | `e2e/scenarios.spec.ts` → "toplu silme" | Eşlendi | P1 |
| TC-030: Execution başlat | `e2e/executions.spec.ts` → "execution" | Eşlendi | P0 |
| TC-040: Akış oluştur | `e2e/flows.spec.ts` → "akış" | Eşlendi | P1 |
| TC-050: Regresyon seti | `e2e/regression.spec.ts` → "regresyon" | Eşlendi | P1 |
| TC-060: Onay süreci | `e2e/approvals.spec.ts` → "onay" | Eşlendi | P1 |
| TC-070: Dosya import | `e2e/import.spec.ts` → "import" | Eşlendi | P1 |
| TC-004: Session timeout | -- | **Otomasyon yok** | P1 |
| TC-012: Proje arşivle | -- | **Otomasyon yok** | P2 |
| TC-026: Versiyon geçmişi | -- | **Otomasyon yok** | P1 |
| TC-080: Kapsam matrisi | -- | **Otomasyon yok** | P2 |
| TC-090: Rapor üretimi | -- | **Otomasyon yok** | P1 |

### Otomasyon Backlog (Öncelik Sırasına Göre)

| # | Manuel TC | Açıklama | Öncelik | Tahmini Efor |
|---|-----------|----------|---------|-------------|
| 1 | TC-004 | Session timeout testi | P1 | 2 saat |
| 2 | TC-026 | Versiyon geçmişi kontrolü | P1 | 3 saat |
| 3 | TC-090 | Rapor üretimi doğrulama | P1 | 4 saat |
| 4 | TC-012 | Proje arşivleme akışı | P2 | 2 saat |
| 5 | TC-080 | Kapsam matrisi UI testi | P2 | 3 saat |

## 5. Risk-Based Coverage

### Risk Matrisi

```
              Etki
         Düşük  Orta  Yüksek  Kritik
Olasılık ┌──────┬──────┬───────┬───────┐
Yüksek   │  L   │  M   │  H    │  C    │
Orta     │  L   │  M   │  H    │  H    │
Düşük    │  L   │  L   │  M    │  M    │
         └──────┴──────┴───────┴───────┘

L = Low    → Minimal test (smoke)
M = Medium → Standard regression
H = High   → Full regression + edge cases
C = Critical → Full + stress + negative + security
```

| Risk Bölgesi | Gerekli Min. Coverage | Mevcut | Hedef | Durum |
|-------------|----------------------|--------|-------|-------|
| Critical (C) | 95% | 87.5% | 95% | Gap: 7.5% |
| High (H) | 85% | 75% | 85% | Gap: 10% |
| Medium (M) | 70% | 60% | 70% | Gap: 10% |
| Low (L) | 50% | 40% | 50% | Gap: 10% |

## 6. Gap Analizi ve Aksiyon Planı

### Tespit Edilen Boşluklar

| # | Gap Türü | Alan | Açıklama | Aksiyon | Sorumlu | Hedef Tarih |
|---|----------|------|----------|---------|---------|-------------|
| G-001 | Requirement Gap | RPT-001 | Rapor üretimi tamamen kapsanmıyor | Manuel + otomasyon TC yaz | QA Lead | Sprint+1 |
| G-002 | Automation Gap | AUTH-003 | Session timeout otomasyonu yok | E2E test yaz | QA Eng | Sprint+1 |
| G-003 | Automation Gap | SCN-002 | Versiyonlama otomasyonu yok | E2E test yaz | QA Eng | Sprint+1 |
| G-004 | Feature Gap | Coverage | Raporlama modülü test yok | Modul tasarla ve test yaz | QA Lead | Sprint+2 |
| G-005 | Feature Gap | API Test | API testing modülü kapsanmıyor | API test senaryoları | QA Eng | Sprint+2 |
