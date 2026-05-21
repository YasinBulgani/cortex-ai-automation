@api @executions @TS-06
Feature: Test Kosulari (Execution)
  Senaryolar test kosularina eklenir, calistirilir,
  sonuclari takip edilir ve tekrar calistirilabilir.

  Arka plan: Proje ve senaryolar hazir
    Given kullanici oturum acmis
    And bir test projesi olusturulmus
    And projede en az 3 senaryo olusturulmus

  # -- TC-0601 --
  @critical @positive @TC-0601
  Scenario: Yeni test kosusu olusturma
    When senaryo ID'leri ile "Sprint-1 Kosusu" adli kosu olusturulur
    Then HTTP yanit kodu 201 olmalidir
    And yanit "status" alani "running" olmalidir
    And yanit "scenario_total" alani 3 olmalidir
    And yanit "passed_count" alani 0 olmalidir

  # -- TC-0602 --
  @high @positive @TC-0602
  Scenario: Kosu detayinda tum senaryo sonuclari listelenir
    Given bir test kosusu olusturulmus
    When kosu detayi istenir
    Then her senaryo icin "pending" statusunde sonuc kaydi bulunmalidir
    And her sonuc kaydinda "scenario_title" alani dolu olmalidir

  # -- TC-0603 --
  @critical @positive @TC-0603
  Scenario: Bireysel senaryo sonucu guncellenir
    Given bir test kosusu olusturulmus
    When ilk sonuc kaydinin statusu "passed" olarak guncellenir
    Then kosu detayindaki ilgili sonuc "passed" olmalidir

  # -- TC-0604 --
  @high @positive @TC-0604
  Scenario: Mevcut kosu yeniden calistirilir
    Given bir test kosusu olusturulmus
    When kosu re-run istegi gonderilir
    Then HTTP yanit kodu 201 olmalidir
    And yeni kosunun adi "(re-run)" son eki icermelidir
    And yeni kosunun senaryo sayisi orijinal ile ayni olmalidir

  # -- TC-0605 --
  @medium @negative @TC-0605
  Scenario: Var olmayan kosu ID ile re-run 404 doner
    When var olmayan kosu ID ile re-run istegi gonderilir
    Then HTTP yanit kodu 404 olmalidir

  # -- TC-0606 --
  @medium @boundary @TC-0606
  Scenario: Bos senaryo listesi ile kosu olusturma
    When bos senaryo listesi ile kosu olusturulur
    Then HTTP yanit kodu 201 olmalidir
    And yanit "scenario_total" alani 0 olmalidir
