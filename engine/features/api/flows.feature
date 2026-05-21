@api @flows @TS-08
Feature: Akis Editoru (Flows)
  Akislar olusturulur ve graf verisi (nodes/edges) guncellenir.

  Arka plan: Proje hazir
    Given kullanici oturum acmis
    And bir test projesi olusturulmus

  # -- TC-0801 --
  @high @positive @TC-0801
  Scenario: Gecerli isimle yeni akis olusturulur
    When "Login Akisi" ismiyle yeni akis olusturulur
    Then HTTP yanit kodu 201 olmalidir
    And yanit "name" alani "Login Akisi" olmalidir

  # -- TC-0802 --
  @high @positive @TC-0802
  Scenario: Akis grafi guncellenir
    Given projede bir akis olusturulmus
    When akisin nodes ve edges verisi guncellenir
    Then akis detayinda guncel nodes ve edges donmelidir

  # -- TC-0803 --
  @medium @boundary @TC-0803
  Scenario: Bos isimle akis olusturulamaz
    When "" ismiyle yeni akis olusturulur
    Then HTTP yanit kodu 422 olmalidir
