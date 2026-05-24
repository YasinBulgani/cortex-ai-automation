# Bu dosya yeni proje şablonunun başlangıç feature dosyasıdır.
# Gerçek senaryolarınızı buraya ekleyin veya yeni .feature dosyaları oluşturun.
Feature: MyProject — Başlangıç Senaryoları

  Background:
    Given kullanıcı oturum açmış durumda

  @smoke
  Scenario: Ana sayfanın yüklenmesi
    When kullanıcı ana sayfaya gider
    Then sayfa başarıyla yüklenir
    And sayfa başlığı görünürdür

  @smoke
  Scenario: Temel navigasyon çalışıyor
    When kullanıcı "dashboard" bağlantısına tıklar
    Then dashboard sayfası açılır

  @regression
  Scenario Outline: Form doğrulama
    Given kullanıcı form sayfasındadır
    When kullanıcı "<alan>" alanına "<deger>" girer
    Then "<beklenen_mesaj>" mesajı görünür

    Examples:
      | alan   | deger         | beklenen_mesaj          |
      | email  | gecersiz@mail | Geçerli e-posta giriniz |
      | email  | test@test.com | Kayıt başarılı          |
