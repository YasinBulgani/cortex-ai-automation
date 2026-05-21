@api @dashboard @TS-16
Feature: Dashboard
  Proje dashboard'u senaryo sayisi, bekleyen onaylar,
  import sayisi ve kosu istatistiklerini gosterir.

  Arka plan: Oturum acilmis
    Given kullanici oturum acmis

  # -- TC-1601 --
  @high @positive @TC-1601
  Scenario: Proje dashboard'u dogru istatistikleri doner
    Given projede senaryolar, onaylar, importlar ve kosular mevcut
    When proje dashboard istegi gonderilir
    Then HTTP yanit kodu 200 olmalidir
    And yanit "scenario_count" alani 0'dan buyuk olmalidir
    And yanit "pending_approvals" alani sayi olmalidir
    And yanit "execution_count" alani sayi olmalidir

  # -- TC-1602 --
  @medium @boundary @TC-1602
  Scenario: Bos proje dashboard'u sifir degerler doner
    Given yeni olusturulmus bos bir proje mevcut
    When proje dashboard istegi gonderilir
    Then HTTP yanit kodu 200 olmalidir
    And yanit "scenario_count" alani 0 olmalidir
    And yanit "pending_approvals" alani 0 olmalidir
    And yanit "execution_count" alani 0 olmalidir
