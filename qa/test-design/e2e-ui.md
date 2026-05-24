# BGTS Test Dönüşüm — E2E / UI Test Senaryoları

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03  
**Platform:** Next.js 14 (React 18) + Playwright  
**Mevcut E2E Dosyaları:** `e2e/login.spec.ts`, `e2e/projects.spec.ts`, `e2e/scenarios.spec.ts`, `e2e/executions.spec.ts`, `e2e/approvals.spec.ts`, `e2e/flows.spec.ts`, `e2e/regression.spec.ts`

---

## 1. Mevcut E2E Kapsam Analizi

| E2E Dosya | Mevcut Test Sayısı | Kapsam |
|-----------|-------------------|--------|
| `login.spec.ts` | 17 | Sayfa yükleme, form validasyon, başarılı/başarısız giriş, erişilebilirlik, API auth |
| `projects.spec.ts` | 3 | Liste, oluşturma, dashboard navigasyon |
| `scenarios.spec.ts` | 4 | Oluşturma, düzenleme, arama, toplu silme |
| `executions.spec.ts` | 2 | Oluşturma, detay görüntüleme |
| `approvals.spec.ts` | 3 | Liste, onaylama, reddetme |
| `flows.spec.ts` | 2 | Oluşturma, editör yükleme |
| `regression.spec.ts` | 2 | Set oluşturma, AI önerisi |
| `smoke.spec.ts` | 1 | Register → Login → Proje → Senaryo → Onay zinciri |

**Toplam mevcut:** 34 E2E test

---

## 2. EKSİK E2E Senaryoları (Yeni Eklenmesi Gereken)

### TS-E2E-01: Login Sayfası — Genişletilmiş

| ID | Başlık | Tip | Öncelik | Durum |
|----|--------|-----|---------|-------|
| E2E-0101 | Şifre alanında gizle/göster toggle'ı çalışmalı | Pozitif | Medium | EKSİK |
| E2E-0102 | Tab tuşu ile form alanları arasında geçiş | Pozitif | Medium | EKSİK |
| E2E-0103 | Enter tuşu ile form submit edilebilmeli | Pozitif | Medium | EKSİK |
| E2E-0104 | Dark/Light tema toggle'ı çalışmalı (varsa) | Pozitif | Low | EKSİK |
| E2E-0105 | Mobil viewport'ta (375px) responsive layout | Pozitif | Medium | EKSİK |
| E2E-0106 | Tablet viewport'ta (768px) responsive layout | Pozitif | Low | EKSİK |

### TS-E2E-02: Proje Yönetimi — Genişletilmiş

| ID | Başlık | Tip | Öncelik | Durum |
|----|--------|-----|---------|-------|
| E2E-0201 | Boş proje durumunda (empty state) mesaj gösterilmeli | Pozitif | Medium | EKSİK |
| E2E-0202 | Proje kartı üzerinde senaryo sayısı gösterilmeli | Pozitif | Medium | EKSİK |
| E2E-0203 | Proje silme işlemi (varsa) | Pozitif | High | EKSİK |
| E2E-0204 | Proje arşivleme işlemi | Pozitif | Medium | EKSİK |
| E2E-0205 | Dashboard metrik kartlarının doğru değer göstermesi | Pozitif | High | EKSİK |
| E2E-0206 | Dashboard'tan hızlı aksiyon butonları çalışmalı | Pozitif | Medium | EKSİK |
| E2E-0207 | Breadcrumb navigasyonu doğru çalışmalı | Pozitif | Medium | EKSİK |

### TS-E2E-03: Senaryo Yönetimi — Genişletilmiş

| ID | Başlık | Tip | Öncelik | Durum |
|----|--------|-----|---------|-------|
| E2E-0301 | Senaryo detay sayfası tam yüklenmeli | Pozitif | High | EKSİK |
| E2E-0302 | Senaryo adımları ekleme/silme/sıralama | Pozitif | Critical | EKSİK |
| E2E-0303 | Senaryo versiyon geçmişi görüntüleme | Pozitif | High | EKSİK |
| E2E-0304 | Senaryo versiyon diff görüntüleme | Pozitif | Medium | EKSİK |
| E2E-0305 | Senaryo durumu değişikliği (draft → active → archived) | Pozitif | High | EKSİK |
| E2E-0306 | Senaryo listeleme sayfalandırma (varsa) | Pozitif | Medium | EKSİK |
| E2E-0307 | BDD senaryo üretimi (AI) — UI akışı | Pozitif | High | EKSİK |
| E2E-0308 | BDD üretim sonuçlarını önizleme ve kaydetme | Pozitif | High | EKSİK |

### TS-E2E-04: Test Koşuları — Genişletilmiş

| ID | Başlık | Tip | Öncelik | Durum |
|----|--------|-----|---------|-------|
| E2E-0401 | Koşu sonucu güncelleme (passed/failed/skipped) | Pozitif | Critical | EKSİK |
| E2E-0402 | Koşu re-run işlemi | Pozitif | High | EKSİK |
| E2E-0403 | Koşu listesinde durum badge'leri doğru gösterilmeli | Pozitif | Medium | EKSİK |
| E2E-0404 | Koşu trend grafikleri doğru render edilmeli | Pozitif | Medium | EKSİK |
| E2E-0405 | Flaky test listesi görüntüleme | Pozitif | Medium | EKSİK |

### TS-E2E-05: Gereksinimler ve Kapsam

| ID | Başlık | Tip | Öncelik | Durum |
|----|--------|-----|---------|-------|
| E2E-0501 | Gereksinim CRUD işlemleri (oluşturma, güncelleme, silme) | Pozitif | High | EKSİK |
| E2E-0502 | Senaryo-gereksinim bağlantı oluşturma UI'dan | Pozitif | High | EKSİK |
| E2E-0503 | Coverage matrix sayfası doğru render edilmeli | Pozitif | High | EKSİK |
| E2E-0504 | Coverage yüzdesi progress bar ile gösterilmeli | Pozitif | Medium | EKSİK |
| E2E-0505 | Coverage gaps listesi görüntüleme | Pozitif | Medium | EKSİK |

### TS-E2E-06: Regresyon Setleri — Genişletilmiş

| ID | Başlık | Tip | Öncelik | Durum |
|----|--------|-----|---------|-------|
| E2E-0601 | Regresyon set detay sayfası ve senaryo listesi | Pozitif | High | EKSİK |
| E2E-0602 | Setten senaryo çıkarma | Pozitif | Medium | EKSİK |
| E2E-0603 | AI öneri sonuçlarını kabul etme | Pozitif | High | EKSİK |
| E2E-0604 | AI öneri sonuçlarını reddetme | Pozitif | Medium | EKSİK |

### TS-E2E-07: Zamanlamalar

| ID | Başlık | Tip | Öncelik | Durum |
|----|--------|-----|---------|-------|
| E2E-0701 | Zamanlama oluşturma formu ve cron expression girişi | Pozitif | High | EKSİK |
| E2E-0702 | Zamanlama etkinleştirme/devre dışı bırakma | Pozitif | Medium | EKSİK |
| E2E-0703 | Zamanlama manuel tetikleme | Pozitif | High | EKSİK |
| E2E-0704 | Zamanlama silme | Pozitif | Medium | EKSİK |

### TS-E2E-08: Test Verisi Yönetimi

| ID | Başlık | Tip | Öncelik | Durum |
|----|--------|-----|---------|-------|
| E2E-0801 | Test veri seti oluşturma (kolon/satır tanımlama) | Pozitif | High | EKSİK |
| E2E-0802 | Veri seti düzenleme (satır ekleme/çıkarma) | Pozitif | High | EKSİK |
| E2E-0803 | Senaryoya veri bağlama UI akışı | Pozitif | High | EKSİK |
| E2E-0804 | Genişletilmiş senaryo önizleme (expanded view) | Pozitif | Medium | EKSİK |

### TS-E2E-09: Entegrasyonlar

| ID | Başlık | Tip | Öncelik | Durum |
|----|--------|-----|---------|-------|
| E2E-0901 | Entegrasyon oluşturma formu | Pozitif | Medium | EKSİK |
| E2E-0902 | Entegrasyon etkinleştirme/devre dışı bırakma | Pozitif | Medium | EKSİK |
| E2E-0903 | Sync butonu ve sonuç gösterimi | Pozitif | Medium | EKSİK |

### TS-E2E-10: Akış Editörü — Genişletilmiş

| ID | Başlık | Tip | Öncelik | Durum |
|----|--------|-----|---------|-------|
| E2E-1001 | React Flow canvas'a node ekleme (drag & drop) | Pozitif | High | EKSİK |
| E2E-1002 | Node'lar arası edge bağlantısı oluşturma | Pozitif | High | EKSİK |
| E2E-1003 | Node properties panel açılması ve düzenleme | Pozitif | Medium | EKSİK |
| E2E-1004 | Akış kaydetme (save) ve yeniden yükleme | Pozitif | High | EKSİK |
| E2E-1005 | Akış simülasyonu çalıştırma | Pozitif | Medium | EKSİK |

### TS-E2E-11: Cross-Cutting / Genel UI

| ID | Başlık | Tip | Öncelik | Durum |
|----|--------|-----|---------|-------|
| E2E-1101 | Sidebar navigasyonu tüm menü öğeleri | Pozitif | High | EKSİK |
| E2E-1102 | Oturum süresi dolduğunda login'e yönlendirme | Negatif | Critical | EKSİK |
| E2E-1103 | 404 sayfası görüntüleme | Pozitif | Medium | EKSİK |
| E2E-1104 | Tema değiştirme (dark/light) | Pozitif | Low | EKSİK |
| E2E-1105 | Profil sayfası görüntüleme | Pozitif | Medium | EKSİK |
| E2E-1106 | Logout işlemi ve token temizleme | Pozitif | Critical | EKSİK |
| E2E-1107 | WebSocket bağlantı durumu göstergesi | Pozitif | Medium | EKSİK |
| E2E-1108 | API hata durumunda kullanıcıya toast/bildirim | Exception | High | EKSİK |

---

## 3. Toplam E2E Kapsam Özeti

| Kategori | Mevcut | Eksik | Toplam Hedef |
|----------|--------|-------|-------------|
| Login | 17 | 6 | 23 |
| Projeler | 3 | 7 | 10 |
| Senaryolar | 4 | 8 | 12 |
| Koşumlar | 2 | 5 | 7 |
| Onaylar | 3 | 0 | 3 |
| Akışlar | 2 | 5 | 7 |
| Regresyon | 2 | 4 | 6 |
| Gereksinimler | 0 | 5 | 5 |
| Zamanlamalar | 0 | 4 | 4 |
| Test Verisi | 0 | 4 | 4 |
| Entegrasyonlar | 0 | 3 | 3 |
| Cross-cutting | 1 | 8 | 9 |
| **Toplam** | **34** | **59** | **93** |
