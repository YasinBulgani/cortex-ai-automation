# Bu dosya TestAutomation proje şablonunun başlangıç feature dosyasıdır.
Feature: TestAutomation — Örnek Test Senaryoları

  Background:
    Given test ortamı hazır

  @smoke
  Scenario: Servis sağlık kontrolü
    When health check endpoint'ine istek atılır
    Then HTTP 200 yanıtı alınır
    And yanıt gövdesi "status" alanı içerir

  @smoke
  Scenario: Kullanıcı girişi doğrulama
    Given geçerli kullanıcı bilgileri mevcuttur
    When kullanıcı giriş yapar
    Then oturum token'ı döner
    And kullanıcı bilgileri erişilebilir olur

  @regression
  Scenario Outline: API endpoint doğrulama
    When "<endpoint>" endpoint'ine GET isteği gönderilir
    Then yanıt kodu <beklenen_kod> olur

    Examples:
      | endpoint    | beklenen_kod |
      | /health     | 200          |
      | /api/v1/me  | 200          |
