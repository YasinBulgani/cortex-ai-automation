# Platform: Web
# URL: www.google.com

Feature: login giris
  Scenario: login giris temel akışı
    Given kullanıcı ana sayfadadır
    When kullanıcı "" metnine tıklar
    Then URL "" içermelidir
