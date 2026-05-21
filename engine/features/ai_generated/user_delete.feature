Feature: Geçersiz JWT ile Kullanıcı Silme

  Background:
    Given API base URL 'http://localhost:8000' ayarlandı
    And Invalid JWT token alındı

  @negative @user
  Scenario: Geçersiz JWT ile kullanıcı silme denemesi
    Given Kullanıcı silme sayfasındadır
    When Kullanıcı silinir
    Then HTTP 401 yanıtı alır