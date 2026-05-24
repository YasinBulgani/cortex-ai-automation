# BGTS Test Dönüşüm — Sentetik Veri Modülü Test Senaryoları

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03  
**Kapsam:** Catalog (Dataset), Rules (RuleSet), Jobs (Generation), Artifacts  
**Router'lar:** `/api/v1/datasets/*`, `/api/v1/jobs/*`

> Bu modüller platformun sentetik veri üretimi tarafını kapsıyor ve ana TSPM (test yönetimi) modülünden ayrıdır.

---

## TS-SD-01: Dataset Catalog Testleri

**Router:** `backend/app/domains/catalog/router.py` (6 endpoint)

| ID | Başlık | Metod | Endpoint | Tip | Öncelik | Beklenen |
|----|--------|-------|----------|-----|---------|----------|
| SD-0101 | Dataset listesi | GET | `/datasets` | Pozitif | High | Array döner; created_at desc sıralı |
| SD-0102 | Dataset oluşturma | POST | `/datasets` | Pozitif | High | 201; id, name, created_by döner |
| SD-0103 | Dataset detay | GET | `/datasets/{id}` | Pozitif | High | Tüm alanlar döner |
| SD-0104 | Var olmayan dataset | GET | `/datasets/invalid-id` | Negatif | Medium | 404 |
| SD-0105 | Dataset oluşturma audit log | POST | `/datasets` | Pozitif | Medium | Audit log'da `dataset.create` kaydı |
| SD-0106 | Dataset version oluşturma | POST | `/datasets/{id}/versions` | Pozitif | High | Version kaydı ve schema_snapshot oluşturulur |
| SD-0107 | Dataset version listesi | GET | `/datasets/{id}/versions` | Pozitif | Medium | Versions desc sıralı |
| SD-0108 | Schema snapshot | GET | `/datasets/{id}/versions/{vid}/schema` | Pozitif | Medium | SchemaSnapshot döner |
| SD-0109 | Boş isimle dataset oluşturma | POST | `/datasets` | Boundary | Medium | 422 |
| SD-0110 | Token olmadan dataset erişimi | GET | `/datasets` | Negatif | Critical | 401/403 |

---

## TS-SD-02: Rule Set Testleri

**Router:** `backend/app/domains/rules/router.py` (3 endpoint)

| ID | Başlık | Metod | Endpoint | Tip | Öncelik | Beklenen |
|----|--------|-------|----------|-----|---------|----------|
| SD-0201 | Rule set listesi | GET | `/datasets/{id}/rule-sets` | Pozitif | High | Array döner |
| SD-0202 | Rule set oluşturma | POST | `/datasets/{id}/rule-sets` | Pozitif | High | 201; name, rules_json döner |
| SD-0203 | Var olmayan dataset ile rule set | POST | `/datasets/invalid/rule-sets` | Negatif | High | 404; "Veri seti bulunamadı" |
| SD-0204 | Rule set oluşturma audit log | POST | `/datasets/{id}/rule-sets` | Pozitif | Medium | Audit log kaydı |
| SD-0205 | Boş isimle rule set | POST | `/datasets/{id}/rule-sets` | Boundary | Medium | 422 |

---

## TS-SD-03: Generation Job Testleri

**Router:** `backend/app/domains/jobs/router.py` (5 endpoint)

| ID | Başlık | Metod | Endpoint | Tip | Öncelik | Beklenen |
|----|--------|-------|----------|-----|---------|----------|
| SD-0301 | Job listesi | GET | `/jobs` | Pozitif | High | Array; limit parametresi çalışır |
| SD-0302 | Job oluşturma (enqueue) | POST | `/jobs` | Pozitif | Critical | 202 Accepted; RQ queue'ya eklenir; status: "queued" |
| SD-0303 | Job detay | GET | `/jobs/{id}` | Pozitif | High | Job bilgileri + events |
| SD-0304 | Job events | GET | `/jobs/{id}/events` | Pozitif | Medium | Event listesi sıralı |
| SD-0305 | Job artifacts | GET | `/jobs/{id}/artifacts` | Pozitif | Medium | Artifact listesi |
| SD-0306 | Var olmayan dataset ile job | POST | `/jobs` | Negatif | High | 404 |
| SD-0307 | Var olmayan rule set ile job | POST | `/jobs` | Negatif | High | 404 |
| SD-0308 | Job limit parametresi (max 200) | GET | `/jobs?limit=999` | Boundary | Low | Max 200 döner |
| SD-0309 | Redis erişilemezken job oluşturma | POST | `/jobs` | Exception | High | Anlaşılır hata; 503 Service Unavailable |
| SD-0310 | Job oluşturma audit log | POST | `/jobs` | Pozitif | Medium | Audit log kaydı |

---

## TS-SD-04: Sentetik Veri Üretim Pipeline (Integration)

| ID | Başlık | Senaryo | Tip | Öncelik |
|----|--------|---------|-----|---------|
| SD-0401 | Uçtan uca pipeline | Dataset oluştur → Version → Rule Set → Job → Artifact | Pozitif | Critical |
| SD-0402 | Rule uygulama doğruluğu | Range rule → üretilen değerler min-max aralığında | Pozitif | High |
| SD-0403 | TCKN üretim doğrulaması | Üretilen TCKN'ler algoritmik olarak geçerli | Pozitif | High |
| SD-0404 | IBAN üretim doğrulaması | Üretilen IBAN'lar mod-97 geçerli | Pozitif | High |
| SD-0405 | FK referential integrity | Customer → Account → Transaction zincirinde orphan yok | Pozitif | Critical |
| SD-0406 | PII tespit doğruluğu | TCKN → CRITICAL, e-posta → HIGH, şehir → LOW | Pozitif | High |
| SD-0407 | KVKK kategori eşleştirmesi | Her PII tespitine doğru KVKK kategorisi atanmış | Pozitif | Medium |
| SD-0408 | 10.000 satır üretim performansı | 10K satır < 30 saniye | Performans | Medium |

---

---

## TS-SD-05: Artifact Download Testleri

**Router:** `backend/app/domains/artifacts/router.py` (1 endpoint)

| ID | Başlık | Metod | Endpoint | Tip | Öncelik | Beklenen |
|----|--------|-------|----------|-----|---------|----------|
| SD-0501 | Artifact download başarılı | GET | `/artifacts/{id}/download` | Pozitif | High | FileResponse; doğru mime_type ve filename |
| SD-0502 | Var olmayan artifact | GET | `/artifacts/invalid/download` | Negatif | High | 404; "Artefakt bulunamadı" |
| SD-0503 | Token olmadan artifact download | GET | `/artifacts/{id}/download` | Negatif | Critical | 401/403 |
| SD-0504 | Dosya sistemi path traversal | — | storage_path'te `../` olup olmadığı | Güvenlik | Critical | Path traversal engellenmeli |
| SD-0505 | Büyük dosya indirme (100MB+) | GET | `/artifacts/{id}/download` | Performans | Medium | Streaming ile indirilmeli; timeout yok |

---

## Toplam Sentetik Veri Modülü Test Sayısı: 38

| Kategori | Sayı |
|----------|------|
| Dataset Catalog | 10 |
| Rule Sets | 5 |
| Generation Jobs | 10 |
| Integration Pipeline | 8 |

---

## Güncellenmiş Genel Toplam (TÜM DOKÜMANLAR)

| Doküman | Test Sayısı |
|---------|------------|
| Ana Test Tasarımı (TSPM) | 75 |
| E2E UI Senaryoları | 59 |
| Güvenlik | 33 |
| Performans | 28 |
| RBAC Matrisi | 180+ |
| API Contract | 45+ |
| Cross-Cutting | 42 |
| İleri Seviye | 84 |
| Smoke / Release | 30 |
| Uzmanlaşmış (WS, i18n, Edge) | 49 |
| n8n + AI Chat | 24 |
| Sentetik Veri Modülü | 33 |
| **GENEL TOPLAM** | **682+** |
