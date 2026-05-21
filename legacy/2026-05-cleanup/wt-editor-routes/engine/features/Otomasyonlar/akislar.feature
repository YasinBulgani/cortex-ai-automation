@ui @flows
Feature: BGTS Akis Editoru
  Akis diyagramlari olusturulur ve React Flow editoru ile duzenlenir.

  Background: Kullanici proje icinde
    Given kullanici "/login" sayfasindadir
    When kullanici "EpostaInput" alanina "@username" yazar
    And kullanici "SifreInput" alanina "@password" yazar
    And kullanici "GirisYapButon" elementine tiklar
    And kullanici ilk projenin linkine tiklar
    And kullanici "Akışlar" metnine tiklar

  @high @positive
  Scenario: Akis listesi goruntulenir
    Then sayfa URL'si "/flows" icermelidir

  @critical @positive
  Scenario: Yeni akis olusturma ve editor acilir
    When kullanici "Yeni Akış" metnine tiklar
    And kullanici "AkisAdiInput" alanina "Login Akisi" yazar
    And kullanici "AkisOlusturButon" elementine tiklar
    Then sayfa URL'si "/flows/" icermelidir
