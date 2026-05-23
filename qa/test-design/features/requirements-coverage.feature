# language: tr

Özellik: Gereksinimler ve Kapsam Matrisi
  Gereksinimler oluşturulur, senaryolara bağlanır ve kapsam analizi yapılır.

  Arka plan:
    Diyelim ki kullanıcı oturum açmış
    Ve projede senaryolar mevcut

  @high @pozitif
  Senaryo: Yeni gereksinim oluşturma
    Diyelim ki gereksinim verisi hazırlanıyor
    Ve external_id "REQ-001" olarak belirleniyor
    Ve başlık "Kullanıcı login yapabilmeli" olarak belirleniyor
    Ve öncelik "high" olarak belirleniyor
    O zaman POST ".../requirements" isteği gönderilir
    Ve yanıt kodu 201 olmalı
    Ve yanıtta "scenario_count" değeri 0 olmalı

  @high @pozitif
  Senaryo: Senaryo ile gereksinim ilişkilendirme
    Diyelim ki "REQ-001" gereksinimi ve "Login Testi" senaryosu mevcut
    O zaman senaryo-gereksinim bağlantı isteği gönderilir
    Ve yanıt başarılı olmalı
    Ve gereksinim listesinde "REQ-001" için scenario_count 1 olmalı

  @medium @boundary
  Senaryo: Duplicate bağlantı ekleme (idempotent)
    Diyelim ki "REQ-001" ve "Login Testi" zaten bağlantılı
    O zaman aynı bağlantı tekrar gönderilir
    Ve yanıt başarılı olmalı
    Ve scenario_count hâlâ 1 olmalı

  @high @pozitif
  Senaryo: Kapsam matrisi hesaplama
    Diyelim ki projede 3 gereksinim mevcut
    Ve 2 gereksinim senaryolara bağlı
    Ve 1 gereksinim bağlantısız
    O zaman GET ".../coverage-matrix" isteği gönderilir
    Ve yanıtta "total_requirements" değeri 3 olmalı
    Ve yanıtta "covered_count" değeri 2 olmalı
    Ve yanıtta "coverage_percent" yaklaşık 66.7 olmalı

  @high @pozitif
  Senaryo: Kapsam boşluklarını tespit etme
    Diyelim ki 1 gereksinim hiçbir senaryoya bağlı değil
    O zaman GET ".../coverage-gaps" isteği gönderilir
    Ve yanıtta 1 gereksinim dönmeli
    Ve bu gereksinim bağlantısız olan olmalı

  @high @pozitif
  Senaryo: Gereksinim silme cascade bağlantı temizliği
    Diyelim ki "REQ-002" gereksinimi bir senaryoya bağlı
    O zaman DELETE ".../requirements/{REQ-002-id}" isteği gönderilir
    Ve yanıt kodu 204 olmalı
    Ve coverage matrix'te "REQ-002" artık görünmemeli

  @medium @boundary
  Senaryo: Boş external_id ile gereksinim oluşturma
    Diyelim ki external_id "" olarak belirleniyor
    O zaman POST ".../requirements" isteği gönderilir
    Ve yanıt kodu 422 olmalı
