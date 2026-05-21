@ui @scenarios
Feature: BGTS Senaryo Yonetimi
  Test senaryolari olusturulur, duzenlenir ve listelenir.

  Background: Kullanici proje icinde
    Given kullanici "/login" sayfasindadir
    When kullanici "EpostaInput" alanina "@username" yazar
    And kullanici "SifreInput" alanina "@password" yazar
    And kullanici "GirisYapButon" elementine tiklar
    And kullanici ilk projenin linkine tiklar
    And kullanici "Senaryolar" metnine tiklar

  @critical @positive
  Scenario: Senaryo listesi goruntulenir
    Then sayfa URL'si "/scenarios" icermelidir

  @critical @positive
  Scenario: Yeni senaryo olusturma
    When kullanici "Yeni Senaryo" metnine tiklar
    And kullanici "SenaryoBaslikInput" alanina "Login Smoke Testi" yazar
    And kullanici "SenaryoAciklamaInput" alanina "Giris fonksiyonelligini dogrular" yazar
    And kullanici "SenaryoKaydetButon" elementine tiklar
    Then sayfa URL'si "/scenarios/" icermelidir

  @high @positive
  Scenario: Senaryo arama filtresi calisir
    When kullanici "SenaryoAramaInput" alanina "Login" yazip Enter'a basar
    Then sayfa URL'si "q=Login" icermelidir

  @high @positive
  Scenario: Senaryo detay sayfasi acilir
    When kullanici ilk senaryonun linkine tiklar
    Then sayfa URL'si "/scenarios/" icermelidir
