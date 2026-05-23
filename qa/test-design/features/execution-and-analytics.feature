# language: tr

Özellik: Test Koşuları ve Analitikler
  Test senaryoları koşulara eklenir, çalıştırılır, sonuçları güncellenir
  ve trend/istatistik analizleri yapılır.

  Arka plan:
    Diyelim ki kullanıcı oturum açmış
    Ve projede 5 senaryo mevcut

  @critical @pozitif
  Senaryo: Yeni test koşusu oluşturma
    Diyelim ki 3 senaryo ID'si ile koşu oluşturma verisi hazırlanıyor
    Ve koşu adı "Sprint-1 Smoke" olarak belirleniyor
    O zaman POST ".../executions" isteği gönderilir
    Ve yanıt kodu 201 olmalı
    Ve yanıtta "status" değeri "running" olmalı
    Ve yanıtta "scenario_total" değeri 3 olmalı
    Ve yanıtta "passed_count" değeri 0 olmalı
    Ve yanıtta "failed_count" değeri 0 olmalı

  @critical @pozitif
  Senaryo: Koşu sonucu güncelleme
    Diyelim ki "Sprint-1" koşusu oluşturulmuş ve 2 senaryo sonucu mevcut
    O zaman ilk sonucun statusü "passed" olarak güncellenir
    Ve ikinci sonucun statusü "failed" olarak güncellenir
    Ve koşu detayı çekildiğinde 1 passed, 1 failed görünmeli

  @high @pozitif
  Senaryo: Koşu tekrar çalıştırma (Re-run)
    Diyelim ki "Sprint-1" koşusu tamamlanmış
    O zaman bu koşu için re-run isteği gönderilir
    Ve yanıt kodu 201 olmalı
    Ve yeni koşu adı "Sprint-1 (re-run)" olmalı
    Ve yeni koşudaki tüm sonuçlar "pending" statusünde olmalı

  @medium @pozitif
  Senaryo: Flaky test tespiti
    Diyelim ki "Login Testi" senaryosu Koşu-1'de "passed", Koşu-2'de "failed"
    O zaman flaky-tests endpoint'i çağrılır
    Ve yanıtta "Login Testi" senaryosu bulunmalı
    Ve flip_count en az 1 olmalı

  @medium @pozitif
  Senaryo: Koşu trend verileri
    Diyelim ki son 7 günde 3 koşu gerçekleştirilmiş
    O zaman execution-trends endpoint'i "?days=7" ile çağrılır
    Ve yanıtta data_points listesi boş olmamalı
    Ve her data point'te "date", "total", "passed", "failed", "pass_rate" alanları olmalı

  @medium @boundary
  Senaryo: Boş senaryo listesi ile koşu oluşturma
    Diyelim ki boş senaryo listesi ile koşu oluşturma verisi hazırlanıyor
    O zaman POST ".../executions" isteği gönderilir
    Ve yanıt kodu 201 olmalı
    Ve yanıtta "scenario_total" değeri 0 olmalı

  @high @negatif
  Senaryo: Var olmayan koşu ID ile erişim
    O zaman GET ".../executions/nonexistent-id" isteği gönderilir
    Ve yanıt kodu 404 olmalı
