@api @requirements @coverage @TS-10
Feature: Gereksinimler ve Kapsam Matrisi
  Gereksinimler olusturulur, senaryolara baglanir
  ve kapsam matrisi ile bosluklar hesaplanir.

  Arka plan: Proje hazir
    Given kullanici oturum acmis
    And bir test projesi olusturulmus

  # -- TC-1001 --
  @high @positive @TC-1001
  Scenario: Gecerli bilgilerle gereksinim olusturulur
    When "REQ-001" kimlikli "Login Fonksiyonu" baslikli gereksinim olusturulur
    Then HTTP yanit kodu 201 olmalidir
    And yanit "scenario_count" alani 0 olmalidir

  # -- TC-1002 --
  @high @positive @TC-1002
  Scenario: Senaryo ile gereksinim basariyla iliskilendirilir
    Given projede bir senaryo olusturulmus
    And projede bir gereksinim olusturulmus
    When senaryo ile gereksinim iliskilendirilir
    Then gereksinim detayinda "scenario_count" 1 olmalidir

  # -- TC-1003 --
  @medium @boundary @TC-1003
  Scenario: Ayni baglanti tekrar eklendiginde duplicate olusmaz
    Given senaryo-gereksinim baglantisi mevcut
    When ayni baglanti tekrar gonderilir
    Then gereksinim detayinda "scenario_count" hala 1 olmalidir

  # -- TC-1004 --
  @high @positive @TC-1004
  Scenario: Kapsam matrisi dogru hesaplanir
    Given projede 3 gereksinim olusturulmus
    And 2 gereksinim senaryolara baglanmis
    When kapsam matrisi istenir
    Then "total_requirements" 3 olmalidir
    And "covered_count" 2 olmalidir
    And "coverage_percent" yaklasik 66.7 olmalidir

  # -- TC-1005 --
  @high @positive @TC-1005
  Scenario: Senaryo kapsaminda olmayan gereksinimler listelenir
    Given projede baglanmamis gereksinimler mevcut
    When kapsam bosluklari istenir
    Then baglanmamis gereksinimler listede gorulmalidir

  # -- TC-1006 --
  @high @positive @TC-1006
  Scenario: Gereksinim silindiginde baglantilari da temizlenir
    Given senaryo-gereksinim baglantisi mevcut
    When gereksinim silinir
    Then HTTP yanit kodu 204 olmalidir
    And kapsam matrisinde ilgili gereksinim bulunmamalidir

  # -- TC-1007 --
  @medium @boundary @TC-1007
  Scenario: Bos external_id ile gereksinim olusturulamaz
    When "" kimlikli gereksinim olusturma istegi gonderilir
    Then HTTP yanit kodu 422 olmalidir
