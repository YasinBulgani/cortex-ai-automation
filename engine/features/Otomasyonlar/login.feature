@ui @login @smoke
Feature: BGTS Platform Giris Sayfasi
  Kullanicilar BGTS platformuna e-posta ve sifre ile giris yapar.

  Background: Login sayfasi acik
    Given kullanici "/login" sayfasindadir

  @critical @positive
  Scenario: Basarili giris ile projeler sayfasina yonlendirilir
    When kullanici "EpostaInput" alanina "@username" yazar
    And kullanici "SifreInput" alanina "@password" yazar
    And kullanici "GirisYapButon" elementine tiklar
    Then sayfa URL'si "/projects" icermelidir

  @critical @negative
  Scenario: Yanlis sifre ile hata mesaji goruntulenir
    When kullanici "EpostaInput" alanina "@username" yazar
    And kullanici "SifreInput" alanina "YanlisSifre123" yazar
    And kullanici "GirisYapButon" elementine tiklar
    Then "HataMesajiText" elementi gorunur olmalidir

  @high @positive
  Scenario: Login sayfasi tum bilesenlerini icerir
    Then "BgtestLogo" elementi gorunur olmalidir
    And "EpostaInput" elementi gorunur olmalidir
    And "SifreInput" elementi gorunur olmalidir
    And "GirisYapButon" elementi gorunur olmalidir
    And "BeniHatirlaCheckbox" elementi gorunur olmalidir
    And "SifremiUnuttumLink" elementi gorunur olmalidir

  @medium @boundary
  Scenario: Bos e-posta ile giris yapilamaz
    When kullanici "SifreInput" alanina "herhangi" yazar
    And kullanici "GirisYapButon" elementine tiklar
    Then sayfa URL'si "/login" icermelidir

  @medium @boundary
  Scenario: Gecersiz e-posta formati ile giris yapilamaz
    When kullanici "EpostaInput" alanina "gecersiz-email" yazar
    And kullanici "SifreInput" alanina "sifre123" yazar
    And kullanici "GirisYapButon" elementine tiklar
    Then sayfa URL'si "/login" icermelidir
