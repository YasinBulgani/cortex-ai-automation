@security @sql_injection @owasp_a03
Feature: SQL Injection Prevention
  Uygulamanın SQL injection saldırılarına karşı korunması.
  Tüm giriş verileri parametrelenerek ve escape edilerek işlenmelidir.

  Background:
    Given backend servisi ayakta
    And admin kullanicisi seed edilmis

  @critical @test_01
  Scenario: OR 1=1 payload ile proje sorgulama
    Given kullanici oturum acmis
    When proje listesinde "' OR '1'='1" arama yapilir
    Then HTTP yanit kodu 200 olmalidir
    And yanit SQL syntax hatasi icermemelidir
    And yanit properly formatted olmalidir

  @critical @test_02
  Scenario: UNION SELECT injection tespiti
    Given kullanici oturum acmis
    When proje filtresi ile "active' UNION SELECT * FROM users--" gonderilir
    Then HTTP yanit kodu 200 olmalidir
    And veritabaninda tablo yapisi expose edilmemelidir

  @high @test_03
  Scenario: Zaman bazli blind SQL injection
    Given kullanici oturum acmis
    When proje sorgusuna "'; SELECT pg_sleep(5); --" gonderilir
    Then yanit 5 saniyeden daha kisa surde gelmeli
    And sorgu timeout veya error donmemelidir

  @high @test_04
  Scenario: Stacked queries injection (DROP TABLE)
    Given kullanici oturum acmis
    And projeler tablosu mevcuttur
    When proje filtresi ile "'; DROP TABLE tspm_projects; --" gonderilir
    Then projeler tablosu hala mevcuttur
    And sonraki sorgular basarili olmalidir

  @medium @test_05
  Scenario: Comment-based SQL injection
    Given kullanici oturum acmis
    When proje arama ile "admin' OR 1=1 #" gonderilir
    Then yanit basarili olmalidir
    And istenmeyen veriler expose edilmemelidir

  @medium @test_06
  Scenario: JSON body icinde SQL injection
    Given kullanici oturum acmis
    When yeni proje olusturulur:
      | name | Test Project' OR '1'='1 |
    Then projeler adi guvenlice depolanmalidir
    And SQL hata donulmemelidir

  @high @test_07
  Scenario: Path parametresinde SQL injection
    Given kullanici oturum acmis
    When /api/v1/tspm/projects/1' OR '1'='1 endpoint'ine istek gonderilir
    Then HTTP yanit kodu 404 veya 422 olmalidir

  @medium @test_08
  Scenario: Toplu islem SQL injection
    Given kullanici oturum acmis
    When bu IDs ile toplu guncelleme yapilir:
      | "1' OR '1'='1" |
      | 2 |
    Then SQL syntax hatasi olmamelidir
    And islem guvenlice sonlanmalidir

  @low @test_09
  Scenario: Parameterize query dogrulamasi
    Given backend parameterized queries kullanmalidir
    When calistirilmis tum queries'ler kontrol edilirse
    Then SQL injection vulnerable query bulunmamalidir

  @medium @test_10
  Scenario: Hata mesajları SQL detaylarini expose etmesin
    Given kullanici oturum acmis
    When geçersiz sorgu gonderilir
    Then yanit hata mesaji su bilgileri icermemelidir:
      | table |
      | column |
      | postgresql |
      | sqlalchemy |
