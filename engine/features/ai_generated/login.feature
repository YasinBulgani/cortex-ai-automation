Feature: Boş e-posta ile giriş denemesi

  Background:
    Given API base URL 'http://localhost:8000' ayarlandı

  @edge_case @auth
  Scenario: Boş e-posta ile giriş denemesi
    Given Kullanıcı login sayfasındadır
    When Email '' ve şifre 'UserPass1!' ile giriş yapar
    Then HTTP 400 yanıtı alır