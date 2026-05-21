@api @schedules @TS-11
Feature: Zamanlamalar (Schedules)
  Cron ifadesi ile periyodik kosular zamanlanir,
  tetiklenir ve senaryo kaynaklari kontrol edilir.

  Arka plan: Proje hazir
    Given kullanici oturum acmis
    And bir test projesi olusturulmus

  # -- TC-1101 --
  @high @positive @TC-1101
  Scenario: Cron ifadesi ile zamanlama olusturulur
    Given projede en az 1 senaryo mevcut
    When "Gece Kosusu" adli "0 2 * * *" cron ile zamanlama olusturulur
    Then HTTP yanit kodu 201 olmalidir
    And yanit "is_active" alani true olmalidir

  # -- TC-1102 --
  @high @positive @TC-1102
  Scenario: Zamanlama manuel tetiklendiginde kosu olusturulur
    Given aktif bir zamanlama ve senaryolari mevcut
    When zamanlama tetiklenir
    Then HTTP yanit kodu 201 olmalidir
    And yeni kosunun adi "Scheduled:" on eki icermelidir
    And zamanlamanin "last_run_at" alani guncellenmis olmalidir

  # -- TC-1103 --
  @high @negative @TC-1103
  Scenario: Senaryosuz zamanlama tetiklendiginde 400 doner
    Given senaryo atamasi olmayan bir zamanlama mevcut
    When zamanlama tetiklenir
    Then HTTP yanit kodu 400 olmalidir

  # -- TC-1104 --
  @medium @positive @TC-1104
  Scenario: Zamanlama regression set'ten senaryo ceker
    Given zamanlama "scenario_ids" bos ve "regression_set_id" dolu
    And regression set'te senaryolar mevcut
    When zamanlama tetiklenir
    Then kosu regression set'teki senaryolarla olusturulmalidir

  # -- TC-1105 --
  @medium @boundary @TC-1105
  Scenario: Bos cron ifadesi ile zamanlama olusturulamaz
    When zamanlama bos cron ifadesi ile olusturma istegi gonderilir
    Then HTTP yanit kodu 422 olmalidir
