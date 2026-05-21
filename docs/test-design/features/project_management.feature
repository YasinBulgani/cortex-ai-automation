# language: tr

Özellik: Proje Yönetimi
  Test ekipleri projeler oluşturur, listeler ve yönetir.
  Her proje test senaryoları, koşular, akışlar ve diğer test varlıklarının kapsayıcısıdır.

  Arka plan:
    Diyelim ki kullanıcı oturum açmış ve geçerli JWT token'a sahip

  @critical @pozitif
  Senaryo: Geçerli bilgilerle yeni proje oluşturma
    Diyelim ki proje oluşturma verisi hazırlanıyor
    Ve proje adı "Sprint-1 Test Projesi" olarak belirleniyor
    Ve proje açıklaması "Sprint 1 kapsamındaki testler" olarak belirleniyor
    O zaman POST "/api/v1/tspm/projects" isteği gönderilir
    Ve yanıt kodu 201 olmalı
    Ve yanıtta "id" alanı UUID formatında olmalı
    Ve yanıtta "name" değeri "Sprint-1 Test Projesi" olmalı
    Ve yanıtta "archived" değeri false olmalı

  @high @boundary
  Senaryo: Boş isim ile proje oluşturulamaz
    Diyelim ki proje oluşturma verisi hazırlanıyor
    Ve proje adı "" olarak belirleniyor
    O zaman POST "/api/v1/tspm/projects" isteği gönderilir
    Ve yanıt kodu 422 olmalı

  @medium @boundary
  Senaryo: Tek karakterli proje ismi kabul edilir
    Diyelim ki proje oluşturma verisi hazırlanıyor
    Ve proje adı "A" olarak belirleniyor
    O zaman POST "/api/v1/tspm/projects" isteği gönderilir
    Ve yanıt kodu 201 olmalı

  @medium @pozitif
  Senaryo: Projeler oluşturma tarihine göre ters sırada listelenir
    Diyelim ki "İlk Proje" adıyla proje oluşturulmuş
    Ve 1 saniye sonra "İkinci Proje" adıyla proje oluşturulmuş
    O zaman GET "/api/v1/tspm/projects" isteği gönderilir
    Ve yanıt listesinde ilk öğe "İkinci Proje" olmalı

  @high @negatif
  Senaryo: Var olmayan proje ID ile erişim 404 döner
    O zaman GET "/api/v1/tspm/projects/00000000-0000-0000-0000-000000000000/dashboard" isteği gönderilir
    Ve yanıt kodu 404 olmalı
    Ve yanıtta "Proje bulunamadı" mesajı olmalı

  @high @pozitif
  Senaryo: Boş proje dashboard'u sıfır değerler döner
    Diyelim ki yeni boş bir proje oluşturulmuş
    O zaman bu projenin dashboard endpoint'i çağrılır
    Ve yanıtta "scenario_count" değeri 0 olmalı
    Ve yanıtta "pending_approvals" değeri 0 olmalı
    Ve yanıtta "execution_count" değeri 0 olmalı
    Ve yanıtta "latest_run_pass_rate" değeri null olmalı
