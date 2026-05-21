Feature: Geçersiz JWT ile Kullanıcı Bilgilerini Güncelleme

  Background:
    Given API base URL 'http://localhost:8000' ayarlandı
    And Invalid JWT token alındı

  @negative @user
  Scenario: Geçersiz JWT ile kullanıcı bilgileri güncelleme denemesi
    Given Kullanıcı güncelleme sayfasındadır
    When Email 'new_email@test.com', Adı 'NewFirstName' ve Soyadı 'NewLastName' ile güncelleme yapar
    Then HTTP 401 yanıtı alır