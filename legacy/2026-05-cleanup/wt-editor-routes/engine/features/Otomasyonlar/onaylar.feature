@ui @approvals
Feature: BGTS Onay Kuyrugu
  AI tarafindan uretilen taslaklar onay kuyrugundan gecirilir.

  Background: Kullanici proje icinde
    Given kullanici "/login" sayfasindadir
    When kullanici "EpostaInput" alanina "@username" yazar
    And kullanici "SifreInput" alanina "@password" yazar
    And kullanici "GirisYapButon" elementine tiklar
    And kullanici ilk projenin linkine tiklar
    And kullanici "Onaylar" metnine tiklar

  @high @positive
  Scenario: Onay listesi goruntulenir
    Then sayfa URL'si "/approvals" icermelidir

  @critical @positive
  Scenario: Onay kabul edilir
    When kullanici ilk onay satirina tiklar
    And kullanici "OnaylaButon" elementine tiklar
    Then "OnayBasariliMesaj" elementi gorunur olmalidir

  @high @positive
  Scenario: Onay reddedilir
    When kullanici ilk onay satirina tiklar
    And kullanici "ReddetButon" elementine tiklar
    Then "RedBasariliMesaj" elementi gorunur olmalidir
