# BGTS Kalite Kontrol Checklist'i

## A. Sprint Başlangıcı Checklist

### A1. Test Planlama
- [ ] Sprint scope'undaki tüm user story'ler için gereksinim ID'leri tanımlı
- [ ] Her gereksinim için test senaryosu belirlendi
- [ ] Test senaryoları TSPM'de oluşturuldu ve requirement'lara bağlandı
- [ ] Otomasyon adayları belirlendi (P0/P1 senaryolar)
- [ ] Test ortamı (staging) hazır ve erişilebilir
- [ ] Test verileri hazırlandı veya sentetik veri üretildi
- [ ] Regresyon seti güncellendi (yeni senaryo eklenmesi gerekiyor mu?)

### A2. Otomasyon Hazırlığı
- [ ] Yeni sayfa nesneleri (Page Objects) oluşturuldu
- [ ] Yeni E2E testler taslak olarak yazıldı
- [ ] CI/CD pipeline'da test job'ları güncel
- [ ] Test tag'leri doğru atandı (`@smoke`, `@regression`, `@p0`)

---

## B. Geliştirme Süreci Checklist

### B1. Her PR İçin
- [ ] Unit testler yazıldı (yeni kod için)
- [ ] Mevcut testler kırılmadı (`pytest` yeşil)
- [ ] Lint hataları yok (`ruff check`)
- [ ] Type check hataları yok (isteğe bağlı `mypy`)
- [ ] E2E smoke testler geçiyor
- [ ] Code review tamamlandı

### B2. Feature Tamamlama
- [ ] Manuel test senaryoları yürütüldü
- [ ] E2E otomasyon testleri yazıldı
- [ ] API testleri yazıldı (varsa endpoint)
- [ ] Senaryo → Otomasyon eşlemesi güncellendi
- [ ] Coverage matrisi güncellendi
- [ ] Negatif senaryolar test edildi
- [ ] Sınır değer testleri yapıldı

---

## C. Test Execution Checklist

### C1. Çalıştırma Öncesi
- [ ] Test ortamı sağlıklı (health check)
- [ ] Veritabanı seed verileri yüklü
- [ ] Tüm servisler ayakta (Backend, Engine, Frontend)
- [ ] Tarayıcı güncel (Playwright browsers)
- [ ] Önceki test verisi temizlendi (temiz slate)

### C2. Çalıştırma Sırası
- [ ] Smoke testler ilk çalıştırıldı
- [ ] Kritik path testleri (P0) çalıştırıldı
- [ ] Regresyon seti tamamlandı
- [ ] Başarısız testler not edildi
- [ ] Ekran görüntüleri/trace'ler kaydedildi

### C3. Çalıştırma Sonrası
- [ ] Execution raporu üretildi (HTML + JSON)
- [ ] Başarısız testler için root-cause analizi yapıldı
- [ ] Bug ticket'ları oluşturuldu (gerçek bug'lar için)
- [ ] Flaky testler işaretlendi ve stabilize backlog'a eklendi
- [ ] Yönetici özeti hazırlandı
- [ ] Rapor ilgili kişilere dağıtıldı
- [ ] Trend verisi güncellendi

---

## D. Release Checklist

### D1. Release Adayı Doğrulama
- [ ] **Tüm P0 (Critical) testler PASSED**
- [ ] **Tüm P1 (High) testler PASSED veya bilinen sorun**
- [ ] P2+ testlerde kabul edilebilir başarı oranı (>= 80%)
- [ ] Açık kritik/blocker bug yok
- [ ] Regresyon seti tam olarak çalıştırıldı
- [ ] Performance testleri kabul edilebilir
- [ ] Security scan yapıldı (varsa)

### D2. Kapsam Doğrulama
- [ ] Requirement coverage >= 90% (kritik alanlar)
- [ ] Automation coverage >= 70%
- [ ] Yeni özelliklerin tümü test edildi
- [ ] Coverage matrisi güncel ve onaylı

### D3. Dokümantasyon
- [ ] Release notes hazırlandı
- [ ] Bilinen sorunlar listesi güncellendi
- [ ] Test sonuç raporu arşivlendi
- [ ] Traceability matrisi son haliyle kaydedildi

### D4. Onay
- [ ] QA Lead onayı
- [ ] Tech Lead onayı
- [ ] Product Owner onayı
- [ ] Release kararı: GO / NO-GO

---

## E. Kalite Metrikleri Threshold Tablosu

| Metrik | Kırmızı (Fail) | Sarı (Uyarı) | Yeşil (OK) |
|--------|----------------|---------------|-------------|
| Genel Pass Rate | < 75% | 75-85% | > 85% |
| P0 Pass Rate | < 90% | 90-95% | > 95% |
| Automation Rate | < 40% | 40-70% | > 70% |
| Requirement Coverage | < 70% | 70-90% | > 90% |
| Flaky Test Oranı | > 10% | 5-10% | < 5% |
| Avg Execution Time | > 30dk | 20-30dk | < 20dk |
| Defect Leakage | > 10% | 5-10% | < 5% |
| MTTD (Tespit Süresi) | > 24 saat | 8-24 saat | < 8 saat |
| MTTR (Çözüm Süresi) | > 48 saat | 24-48 saat | < 24 saat |

---

## F. Haftalık Kalite Bakım Checklist

### Her Pazartesi
- [ ] Önceki haftanın test sonuçları review edildi
- [ ] Flaky testler listesi güncellendi
- [ ] Yeni otomasyon backlog'u önceliklendirildi
- [ ] Coverage gap'leri değerlendirildi

### Her Cuma
- [ ] Haftalık kalite özeti hazırlandı
- [ ] Trend grafikleri güncellendi
- [ ] Gelecek hafta test planı gözden geçirildi
- [ ] Teknik borç (test) backlog'u güncellendi

---

## G. Aylık Kalite Review Checklist

- [ ] Aylık kalite raporu hazırlandı
- [ ] Test otomasyon ROI hesaplandı
- [ ] Coverage trendi analiz edildi
- [ ] Kalite hedefleri review edildi ve güncellendi
- [ ] Test altyapı iyileştirmeleri planlandı
- [ ] Ekip eğitim ihtiyaçları değerlendirildi
- [ ] Araç/teknoloji güncellemeleri planlandı
- [ ] Süreç iyileştirme önerileri toplandı
