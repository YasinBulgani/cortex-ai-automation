Feature: Geçersiz JWT token ile logout denemesi

  Background:
    Given API base URL 'http://localhost:8000' ayarlandı

  @negative @auth
  Scenario: Geçersiz JWT token ile logout denemesi
    Given Kullanıcı login sayfasındadır
    When Logout işlemi yapılır — Authorization: Bearer invalid_token
    Then HTTP 401 yanıtı alır