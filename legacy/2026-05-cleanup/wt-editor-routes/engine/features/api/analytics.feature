@api @analytics @TS-07
Feature: Kosu Analitikleri
  Son 30 gunluk kosu trend verileri, flaky test tespiti
  ve genel istatistikler raporlanir.

  Arka plan: Proje ve kosular hazir
    Given kullanici oturum acmis
    And bir test projesi olusturulmus
    And projede kosu verileri mevcut

  # -- TC-0701 --
  @medium @positive @TC-0701
  Scenario: Son 30 gunluk kosu trend verileri doner
    When 30 gunluk execution trend istegi gonderilir
    Then HTTP yanit kodu 200 olmalidir
    And yanit "data_points" listesi doner
    And her veri noktasinda "total", "passed", "failed", "pass_rate" alanlari bulunmalidir

  # -- TC-0702 --
  @medium @positive @TC-0702
  Scenario: Flaky testler tespit edilir
    Given ayni senaryo farkli kosularda passed ve failed olmus
    When flaky test listesi istenir
    Then sonuc listesinde ilgili senaryo "flip_count >= 1" ile gorunmelidir

  # -- TC-0703 --
  @medium @positive @TC-0703
  Scenario: Genel kosu istatistikleri dogru hesaplanir
    When kosu istatistikleri istenir
    Then HTTP yanit kodu 200 olmalidir
    And yanit "total_executions" alani 0'dan buyuk olmalidir
    And yanit "avg_pass_rate" alani sayi olmalidir
