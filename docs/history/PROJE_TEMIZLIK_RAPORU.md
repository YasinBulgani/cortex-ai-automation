# TestwrightAI — Proje Temizlik Raporu

> Oluşturulma tarihi: 2026-04-09
> Durum: Tespit edildi — SİLİNMEDİ. Silinmeden önce ekip onayı alınmalıdır.

---

## Özet

| Kategori | Dizin Sayısı | Tahmini Kazanım |
|----------|-------------|-----------------|
| Duplicate AI/Engine modülleri | 3 | ~785 MB |
| Eski sentetik veri versiyonları | 3 | ~334 MB |
| Kullanılmayan framework'ler | 2 | ~60 MB |
| Workspace duplikatları | 1 | ~8 KB |
| **TOPLAM** | **9 dizin** | **~1.18 GB** |

---

## Silinmesi Önerilen Dizinler

### 1. ai-test-automation/ — 784 MB ❗ EN BÜYÜK KAZANIM

| Alan | Detay |
|------|-------|
| **Boyut** | 784 MB |
| **Neden silinebilir** | `ai-test-pipeline/` ile işlevsel örtüşme var. `ai-test-automation/jarvis/` alt modülü node_modules içeriyor (büyüklüğün kaynağı bu). |
| **Risk** | Orta — `jarvis/` içinde özgün kod olabilir. Silmeden önce kontrol et: `ls ai-test-automation/app/` |
| **Öneri** | `ai-test-automation/app/` içindeki özgün Python dosyalarını `backend/app/domains/ai/` altına taşı, sonra dizini sil. |

### 2. backend/synthetic-data-v2/ — 215 MB

| Alan | Detay |
|------|-------|
| **Boyut** | 215 MB |
| **Neden silinebilir** | `synthetic-data/platform-v4/` aktif versiyondur. v2 eskimiş. `banking_core.db` ve `internet_banking_real.db` SQLite dosyaları içeriyor — bu veritabanları gerçek data barındırıyorsa başka yere taşı. |
| **Risk** | Düşük — ancak SQLite dosyalarını yedekle. |
| **Öneri** | SQLite dosyalarını `backend/data/` altına taşı, dizini sil. |

### 3. backend/synthetic-data-v3/ — 119 MB

| Alan | Detay |
|------|-------|
| **Boyut** | 119 MB |
| **Neden silinebilir** | v4 ile çakışıyor. Eski ama aktif versiyonun üzerinde çalışılan ara versiyon. |
| **Risk** | Düşük — v4'te olmayan özgün bir özellik varsa not al. |
| **Öneri** | `diff -r backend/synthetic-data-v3/app backend/synthetic-data-v4/app` ile fark kontrol edilsin, sonra sil. |

### 4. frameworks/Test_Template/ — 57 MB

| Alan | Detay |
|------|-------|
| **Boyut** | 57 MB |
| **Neden silinebilir** | `frameworks/playwright-cucumber-ts/` aktif suite. `Test_Template/` boilerplate/şablon — `scaffolded_projects/` mekanizması bunu zaten gereksiz kılıyor. |
| **Risk** | Düşük — yeni proje şablonu olarak `playwright-cucumber-ts` kullanılıyor. |
| **Öneri** | Şablon ihtiyacı varsa `scaffolded_projects/` sistemine entegre et, sonra sil. |

### 5. ai-test-pipeline/ — 120 KB

| Alan | Detay |
|------|-------|
| **Boyut** | 120 KB |
| **Neden silinebilir** | Tamamı `__pycache__` (derlenmiş .pyc dosyaları). Kaynak kod (.py) yok. |
| **Risk** | Yok — yalnızca bytecode. |
| **Öneri** | Hemen silinebilir: `rm -rf ai-test-pipeline/` |

### 6. frameworks/selenium-cucumber-java/ — 3.2 MB

| Alan | Detay |
|------|-------|
| **Boyut** | 3.2 MB |
| **Neden silinebilir** | Java/Selenium stack — Playwright ile çakışıyor. `tools/aday-degerlendirme/` (Maven) haricinde Java bağımlılığı yok. |
| **Risk** | Düşük — bancılık uygulamasında Java agent gerektiren özel bir senaryo varsa tut. |
| **Öneri** | Aktif kullanım yoksa sil. |

### 7. ai-engine/ — 176 KB

| Alan | Detay |
|------|-------|
| **Boyut** | 176 KB |
| **Neden silinebilir** | TypeScript CLI helper'ları — `backend/` ve `engine/` bunu karşılıyor. |
| **Risk** | Düşük — içeriği kontrol et: `ls ai-engine/src/` |
| **Öneri** | Kullanılan bir özellik yoksa sil. |

### 8. test-automation-workspace/ — 8 KB

| Alan | Detay |
|------|-------|
| **Boyut** | 8 KB |
| **Neden silinebilir** | `exports/` ve `uploads/` klasörleri — büyük ihtimalle boş ya da temp dosyalar. |
| **Risk** | Yok |
| **Öneri** | İçeriğini kontrol et (`ls -la test-automation-workspace/`), boşsa sil. |

### 9. backend/synthetic-data-bgtsflow/ — 116 KB

| Alan | Detay |
|------|-------|
| **Boyut** | 116 KB |
| **Neden silinebilir** | BGTSFlow denemesi — `synthetic-data/platform-v4/` ile çakışıyor. |
| **Risk** | Düşük |
| **Öneri** | Özgün bir iş mantığı yoksa sil. |

---

## Silinmemesi Gerekenler

Bu dizinler duplikat gibi görünse de **tutulmalıdır**:

| Dizin | Neden Tutulmalı |
|-------|-----------------|
| `engine/` | Aktif Flask motoru, `docker-compose.yml` içinde tanımlı |
| `synthetic-data/platform-v4/` | Aktif sentetik veri servisi |
| `backend/banking-data/` | Üretim veritabanı referansları |
| `backend/data/` | Seed ve referans verileri |
| `docs/` | Tüm teknik dokümantasyon |
| `reports/` | Test raporları (Allure, HTML) |
| `scaffolded_projects/` | Dinamik proje çıktıları |

---

## Temizlik Sıralaması (Düşükten Yükseğe Risk)

1. `ai-test-pipeline/` — hemen sil (sadece __pycache__)
2. `test-automation-workspace/` — içerik boşsa sil
3. `backend/synthetic-data-bgtsflow/` — kontrol et, sil
4. `ai-engine/src/` — incele, sil
5. `frameworks/selenium-cucumber-java/` — sil
6. `frameworks/Test_Template/` — sil
7. `backend/synthetic-data-v3/` — diff al, sil
8. `backend/synthetic-data-v2/` — SQLite yedekle, sil
9. `ai-test-automation/` — jarvis/app incele, özgün kodu taşı, sil

---

## Temizlik Komutu (Onaydan Sonra Çalıştır)

```bash
# ÖNCE: git stash veya commit ile değişikliklerini kaydet

# 1. Sadece __pycache__ — güvenli
rm -rf ai-test-pipeline/__pycache__ ai-test-pipeline/app

# 2. SQLite yedekle
cp backend/synthetic-data-v2/*.db backend/data/ 2>/dev/null || true

# 3. Onaylanmış dizinleri sil
# rm -rf ai-test-automation/ backend/synthetic-data-v2/ backend/synthetic-data-v3/
# rm -rf frameworks/Test_Template/ frameworks/selenium-cucumber-java/
# rm -rf ai-engine/ test-automation-workspace/ backend/synthetic-data-bgtsflow/

# 4. Commit
git add -A && git commit -m "chore: remove stale/duplicate modules (~1.18 GB)"
```

---

*Bu rapor otomatik analiz ile oluşturulmuştur. Silme işlemi ekip onayı gerektirir.*
