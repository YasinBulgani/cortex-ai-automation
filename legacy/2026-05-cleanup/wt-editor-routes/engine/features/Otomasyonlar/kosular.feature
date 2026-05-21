@ui @executions
Feature: BGTS Test Kosulari
  Senaryolar test kosularina eklenir ve calistirilir.

  Background: Kullanici proje icinde
    Given kullanici "/login" sayfasindadir
    When kullanici "EpostaInput" alanina "@username" yazar
    And kullanici "SifreInput" alanina "@password" yazar
    And kullanici "GirisYapButon" elementine tiklar
    And kullanici ilk projenin linkine tiklar
    And kullanici "Koşular" metnine tiklar

  @high @positive
  Scenario: Kosu listesi goruntulenir
    Then sayfa URL'si "/executions" icermelidir

  @critical @positive
  Scenario: Yeni kosu olusturma
    When kullanici "Yeni Koşu" metnine tiklar
    And kullanici "KosuAdiInput" alanina "Sprint-1 Kosusu" yazar
    And kullanici ilk senaryo checkbox'ini isaretler
    And kullanici "KosuBaslatButon" elementine tiklar
    Then sayfa URL'si "/executions/" icermelidir

  @high @positive
  Scenario: Kosu detayi goruntulenir
    When kullanici ilk kosunun linkine tiklar
    Then sayfa URL'si "/executions/" icermelidir
