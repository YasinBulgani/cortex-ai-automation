@api @api-tests @TS-14
Feature: API Testi
  API test koleksiyonlari olusturulur,
  request'ler eklenir ve koleksiyon calistirilir.

  Arka plan: Proje hazir
    Given kullanici oturum acmis
    And bir test projesi olusturulmus

  # -- TC-1401 --
  @high @positive @TC-1401
  Scenario: API test koleksiyonu olusturulur
    When "Auth API" adli koleksiyon olusturulur
    Then HTTP yanit kodu 201 olmalidir
    And yanit "request_count" alani 0 olmalidir

  # -- TC-1402 --
  @high @positive @TC-1402
  Scenario: Koleksiyona HTTP request eklenir
    Given projede bir API koleksiyonu olusturulmus
    When koleksiyona "Health Check" adli GET /health request'i eklenir
    Then HTTP yanit kodu 201 olmalidir

  # -- TC-1403 --
  @high @positive @TC-1403
  Scenario: Koleksiyondaki tum request'ler sirayla calistirilir
    Given koleksiyonda en az 1 request mevcut
    When koleksiyon calistirilir
    Then HTTP yanit kodu 200 olmalidir
    And sonuc listesinde her request icin "status_code" ve "passed" alanlari donmelidir

  # -- TC-1404 --
  @medium @exception @TC-1404
  Scenario: Erisilemez URL ile koleksiyon calistirmada hata donmesi
    Given koleksiyonda erisilemez base_url'li request mevcut
    When koleksiyon calistirilir
    Then sonuc listesinde "passed" false ve "error" alani dolu olmalidir
