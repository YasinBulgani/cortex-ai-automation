# language: en

Feature: Proje Yönetimi
  Test ekipleri projeler oluşturur, listeler ve yönetir.
  Her proje test senaryoları, koşular, akışlar ve diğer test varlıklarının kapsayıcısıdır.

  Geçmiş:
    Diyelim ki kullanıcı oturum açmış ve geçerli JWT token'a sahip

  @critical @pozitif
  Scenario: Geçerli bilgilerle yeni proje oluşturma
    Given proje oluşturma verisi hazırlanıyor
    And proje adı "Sprint-1 Test Projesi" olarak belirleniyor
    And proje açıklaması "Sprint 1 kapsamındaki testler" olarak belirleniyor
    When POST "/api/v1/tspm/projects" isteği gönderilir
    Then yanıt kodu 201 olmalı
    And yanıtta "id" alanı UUID formatında olmalı
    And yanıtta "name" değeri "Sprint-1 Test Projesi" olmalı
    And yanıtta "archived" değeri false olmalı

  @high @boundary
  Scenario: Boş isim ile proje oluşturulamaz
    Given proje oluşturma verisi hazırlanıyor
    And proje adı "" olarak belirleniyor
    When POST "/api/v1/tspm/projects" isteği gönderilir
    Then yanıt kodu 422 olmalı

  @medium @boundary
  Scenario: Tek karakterli proje ismi kabul edilir
    Given proje oluşturma verisi hazırlanıyor
    And proje adı "A" olarak belirleniyor
    When POST "/api/v1/tspm/projects" isteği gönderilir
    Then yanıt kodu 201 olmalı

  @medium @pozitif
  Scenario: Projeler oluşturma tarihine göre ters sırada listelenir
    Given "İlk Proje" adıyla proje oluşturulmuş
    And 1 saniye sonra "İkinci Proje" adıyla proje oluşturulmuş
    When GET "/api/v1/tspm/projects" isteği gönderilir
    Then yanıt listesinde ilk öğe "İkinci Proje" olmalı

  @high @negatif
  Scenario: Var olmayan proje ID ile erişim 404 döner
    When GET "/api/v1/tspm/projects/00000000-0000-0000-0000-000000000000/dashboard" isteği gönderilir
    Then yanıt kodu 404 olmalı
    And yanıtta "Proje bulunamadı" mesajı olmalı

  @high @pozitif
  Scenario: Boş proje dashboard'u sıfır değerler döner
    Given yeni boş bir proje oluşturulmuş
    When bu projenin dashboard endpoint'i çağrılır
    Then yanıtta "scenario_count" değeri 0 olmalı
    And yanıtta "pending_approvals" değeri 0 olmalı
    And yanıtta "execution_count" değeri 0 olmalı
    And yanıtta "latest_run_pass_rate" değeri null olmalı
