@api @regression @TS-09
Feature: Regresyon Setleri
  Senaryolar regresyon setlerine gruplanir,
  AI oneri yapar ve oneriler toplu kabul edilir.

  Arka plan: Proje hazir
    Given kullanici oturum acmis
    And bir test projesi olusturulmus

  # -- TC-0901 --
  @high @positive @TC-0901
  Scenario: Gecerli isimle regresyon seti olusturulur
    When "Smoke Seti" ismiyle regresyon seti olusturulur
    Then HTTP yanit kodu 201 olmalidir
    And yanit "scenario_count" alani 0 olmalidir

  # -- TC-0902 --
  @high @positive @TC-0902
  Scenario: Regresyon setine senaryolar eklenir
    Given projede bir regresyon seti olusturulmus
    And projede 2 senaryo olusturulmus
    When 2 senaryonun ID'leri regresyon setine eklenir
    Then set detayinda 2 senaryo bulunmalidir

  # -- TC-0903 --
  @medium @boundary @TC-0903
  Scenario: Ayni senaryo tekrar eklendiginde duplicate olusmaz
    Given regresyon setinde 2 senaryo mevcut
    When ayni senaryo ID'leri tekrar eklenir
    Then set detayindaki senaryo sayisi degismemelidir

  # -- TC-0904 --
  @medium @positive @TC-0904
  Scenario: AI regresyon seti onerisi
    Given projede en az 1 senaryo mevcut
    When AI regresyon seti oneri istegi gonderilir
    Then HTTP yanit kodu 200 olmalidir
    And yanit "sets" listesi en az 1 oneri icermelidir

  # -- TC-0905 --
  @medium @negative @TC-0905
  Scenario: Senaryosu olmayan projede AI onerisi 400 doner
    Given projede hic senaryo yok
    When AI regresyon seti oneri istegi gonderilir
    Then HTTP yanit kodu 400 olmalidir

  # -- TC-0906 --
  @high @positive @TC-0906
  Scenario: AI onerilerinden secilen setler toplu olusturulur
    Given AI regresyon seti onerileri alinmis
    When secilen oneriler kabul edilir
    Then HTTP yanit kodu 201 olmalidir
    And onerilen setler basariyla olusturulmus olmalidir
