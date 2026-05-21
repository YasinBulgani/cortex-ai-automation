@ui @projects
Feature: BGTS Proje Yonetimi
  Kullanicilar projelerini olusturur, listeler ve yonetir.

  Background: Kullanici giris yapmis
    Given kullanici "/login" sayfasindadir
    When kullanici "EpostaInput" alanina "@username" yazar
    And kullanici "SifreInput" alanina "@password" yazar
    And kullanici "GirisYapButon" elementine tiklar
    Then sayfa URL'si "/projects" icermelidir

  @high @positive
  Scenario: Proje listesi sayfasi yuklenir
    Then sayfa basligi "BGTEST" icermelidir

  @critical @positive
  Scenario: Yeni proje olusturma
    When kullanici "Yeni Proje" metnine tiklar
    And kullanici "ProjeAdiInput" alanina "Otomasyon Test Projesi" yazar
    And kullanici "ProjeAciklamaInput" alanina "BDD test projesi" yazar
    And kullanici "ProjeOlusturButon" elementine tiklar
    Then sayfa URL'si "/p/" icermelidir

  @high @positive
  Scenario: Proje dashboard istatistikleri goruntulenir
    When kullanici ilk projenin linkine tiklar
    Then "SenaryoSayisiKart" elementi gorunur olmalidir
    And "KosuSayisiKart" elementi gorunur olmalidir
