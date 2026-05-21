# language: tr
# Platform: Web
# URL: www.google.com
# DB: belirtilmedi

Özellik: login giris
  Senaryo: login giris temel akışı
    Given kullanıcı ana sayfadadır
    When kullanıcı "" metnine tıklar
    Then URL "" içermelidir
