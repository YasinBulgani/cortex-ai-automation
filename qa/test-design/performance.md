# BGTS Test Dönüşüm — Performans ve Yük Test Senaryoları

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03  
**Araçlar:** k6, Locust, Playwright (performance), pytest-benchmark  

---

## 1. Performans Test Hedefleri

| Metrik | Hedef Değer | Kritik Eşik |
|--------|------------|-------------|
| API Response Time (P95) | < 500ms | > 2000ms |
| API Response Time (P99) | < 1000ms | > 5000ms |
| Login Response Time | < 300ms | > 1000ms |
| Sayfa İlk Yükleme (FCP) | < 1.5s | > 3s |
| Sayfa Tam Yükleme (LCP) | < 2.5s | > 4s |
| Eşzamanlı Kullanıcı | 50 | Çökme noktası |
| Throughput | > 100 req/s | < 20 req/s |
| Hata Oranı | < 1% | > 5% |
| Memory Leak | Stabil 30 dakika | Sürekli artış |

---

## 2. API Performans Testleri

### TS-PERF-01: Endpoint Yanıt Süreleri

| ID | Başlık | Metod | Endpoint | Hedef P95 | Yük |
|----|--------|-------|----------|-----------|-----|
| PERF-0101 | Login yanıt süresi | POST | `/api/v1/auth/login` | < 300ms | 50 eşzamanlı |
| PERF-0102 | Proje listesi yanıt süresi | GET | `/tspm/projects` | < 200ms | 100 proje, 20 eşzamanlı |
| PERF-0103 | Senaryo listesi yanıt süresi | GET | `/tspm/projects/{id}/scenarios` | < 300ms | 500 senaryo, 20 eşzamanlı |
| PERF-0104 | Senaryo arama yanıt süresi | GET | `/tspm/projects/{id}/scenarios?q=test` | < 500ms | 1000 senaryo |
| PERF-0105 | Senaryo oluşturma yanıt süresi | POST | `/tspm/projects/{id}/scenarios` | < 500ms | 10 eşzamanlı |
| PERF-0106 | Koşu oluşturma (50 senaryo) yanıt süresi | POST | `/tspm/projects/{id}/executions` | < 1000ms | 50 senaryo |
| PERF-0107 | Dashboard yanıt süresi | GET | `/tspm/projects/{id}/dashboard` | < 300ms | 20 eşzamanlı |
| PERF-0108 | Coverage matrix hesaplama | GET | `/tspm/projects/{id}/coverage-matrix` | < 500ms | 100 gereksinim |
| PERF-0109 | Execution trends hesaplama | GET | `/tspm/projects/{id}/execution-trends` | < 500ms | 30 gün veri |
| PERF-0110 | BDD üretimi (AI) yanıt süresi | POST | `/tspm/projects/{id}/scenarios/generate-bdd` | < 10s | 1 istek |
| PERF-0111 | API test koleksiyonu çalıştırma | POST | `/tspm/.../collections/{id}/run` | < 30s | 10 request |
| PERF-0112 | Flaky test tespiti | GET | `/tspm/projects/{id}/flaky-tests` | < 500ms | 10 koşu |

### TS-PERF-02: Yük Testleri (Load Testing)

| ID | Başlık | Senaryo | Süre | Kullanıcı | Beklenti |
|----|--------|---------|------|-----------|----------|
| PERF-0201 | Normal yük | Tipik kullanım akışı (login → proje → senaryo liste → detay) | 10 dk | 20 eşzamanlı | P95 < 500ms, hata < 1% |
| PERF-0202 | Yoğun yük | Aynı akış | 10 dk | 50 eşzamanlı | P95 < 1000ms, hata < 3% |
| PERF-0203 | Stres testi | Aynı akış, rampa ile artan yük | 15 dk | 10→100 rampa | Degradation graceful olmalı |
| PERF-0204 | Spike testi | Anlık yük patlaması | 5 dk | 0→100→0 spike | Recovery < 30s |
| PERF-0205 | Dayanıklılık (Soak) | Sürekli düşük yük | 60 dk | 10 eşzamanlı | Memory leak yok; yanıt stabil |

### TS-PERF-03: Veritabanı Performansı

| ID | Başlık | Test | Beklenti |
|----|--------|------|----------|
| PERF-0301 | Büyük proje (1000+ senaryo) listesi | 1000 senaryo ile GET list | < 500ms |
| PERF-0302 | Çok sayıda koşu (100+) ile trend | 100 koşu ile execution-trends | < 500ms |
| PERF-0303 | Cascade delete performansı | 100 senaryolu projeyi silme | < 2000ms |
| PERF-0304 | N+1 query kontrolü | Senaryo listesi sorgusunu analiz et | N+1 olmamalı |
| PERF-0305 | Index kullanım kontrolü | EXPLAIN ANALYZE ile sorguları analiz et | Seq scan olmamalı |

### TS-PERF-04: Frontend Performansı

| ID | Başlık | Sayfa | Metrik | Hedef |
|----|--------|-------|--------|-------|
| PERF-0401 | Login sayfası FCP | `/login` | First Contentful Paint | < 1.0s |
| PERF-0402 | Proje listesi LCP | `/projects` | Largest Contentful Paint | < 2.0s |
| PERF-0403 | Senaryo listesi (500 öğe) render | `/p/{id}/scenarios` | Time to Interactive | < 3.0s |
| PERF-0404 | Flow editör başlangıç | `/p/{id}/flows/{fid}` | React Flow render | < 2.0s |
| PERF-0405 | Bundle size kontrolü | - | JS bundle (gzip) | < 300KB |
| PERF-0406 | Lighthouse skoru | Tüm sayfalar | Performance score | > 80 |

---

## 3. Performans Test Senaryosu Detay Örneği (k6 Script Yapısı)

```
k6 Senaryo: Normal Yük Testi
├── Stage 1: Ramp-up (0→20 kullanıcı, 2 dakika)
├── Stage 2: Steady state (20 kullanıcı, 6 dakika)
├── Stage 3: Ramp-down (20→0, 2 dakika)
│
├── VU Akışı:
│   1. POST /auth/login → token al
│   2. GET /tspm/projects → proje listele
│   3. GET /tspm/projects/{id}/dashboard → dashboard
│   4. GET /tspm/projects/{id}/scenarios → senaryo listele
│   5. GET /tspm/projects/{id}/scenarios/{sid} → senaryo detay
│   6. POST /tspm/projects/{id}/scenarios → yeni senaryo
│   7. Sleep 1-3s (think time)
│   8. GET /tspm/projects/{id}/executions → koşu listele
│   9. Sleep 2-5s
│
├── Eşik Değerleri:
│   - http_req_duration P95 < 500ms
│   - http_req_failed < 1%
│   - http_reqs > 100/s
│
└── Çıktı: HTML rapor + JSON metrics
```

---

## Toplam Performans Test Sayısı: 28

| Kategori | Sayı |
|----------|------|
| API Yanıt Süreleri | 12 |
| Yük Testleri | 5 |
| Veritabanı Performansı | 5 |
| Frontend Performansı | 6 |
