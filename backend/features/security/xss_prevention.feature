@security @xss @owasp_a07
Feature: Cross-Site Scripting (XSS) Prevention
  Uygulamanın XSS saldırılarına karşı korunması.
  Tüm user input'lar sanitize edilmeli ve output'lar escape edilmelidir.

  Background:
    Given backend servisi ayakta
    And admin kullanicisi seed edilmis

  @critical @test_01
  Scenario: Reflected XSS - Script tag arama parametresinde
    Given kullanici oturum acmis
    When proje arama parametresi "<script>alert(1)</script>" gonderilir
    Then yanit basarili olmalidir
    And script tag'i escaped veya sanitize olmalidir
    And response'da "<script>" olmamalidir (escaped olmasi gerekir)

  @critical @test_02
  Scenario: Stored XSS - Proje adinda script tag
    Given kullanici oturum acmis
    When proje olusturulur:
      | name | <img src=x onerror=alert('XSS')> |
    And proje detay sayfasi acilir
    Then img tag'i sanitize olmalidir
    And onerror handler'i kaldirulmali

  @high @test_03
  Scenario: SVG onload event handler XSS
    Given kullanici oturum acmis
    When aciklama ile "<svg onload=alert(1)>" gonderilir
    Then onload handler'i neutralize olmalidir

  @high @test_04
  Scenario: JavaScript URL XSS
    Given kullanici oturum acmis
    When proje URL'si "javascript:alert(1)" ile gonderilir
    Then javascript: scheme blocked olmalidir

  @high @test_05
  Scenario: Data URL XSS
    Given kullanici oturum acmis
    When URL parametresi "data:text/html,<script>alert(1)</script>" ile gonderilir
    Then data: scheme blocked olmalidir

  @medium @test_06
  Scenario: HTML entity bypass (&#60;script&#62;)
    Given kullanici oturum acmis
    When arama "&#60;script&#62;alert(1)&#60;/script&#62;" ile yapilir
    Then decoded ve sanitize olmalidir

  @medium @test_07
  Scenario: Unicode escape XSS bypass
    Given kullanici oturum acmis
    When arama "\\u003cscript\\u003e" ile yapilir
    Then unicode decoded ve filtered olmalidir

  @medium @test_08
  Scenario: Case sensitivity bypass (ScRiPt, SCRIPT)
    Given kullanici oturum acmis
    When bu payloads'lar test edilir:
      | <ScRiPt>alert(1)</ScRiPt> |
      | <SCRIPT>alert(1)</SCRIPT> |
    Then hepsi sanitize olmalidir

  @low @test_09
  Scenario: Nested tag XSS
    Given kullanici oturum acmis
    When arama "<script><script>alert(1)</script></script>" ile yapilir
    Then her iki tag'i sanitize olmalidir

  @medium @test_10
  Scenario: API response Content-Type kontrolu
    Given kullanici oturum acmis
    When /api/v1/tspm/projects endpoint'ine istek gonderilir
    Then Content-Type header'i "application/json" olmalidir
    And X-Content-Type-Options: nosniff header'i bulunmalidir

  @high @test_11
  Scenario: IFrame XSS injection
    Given kullanici oturum acmis
    When arama '<iframe src="javascript:alert(1)">' ile yapilir
    Then iframe tag'i kaldirulmali veya src sanitize olmalidir

  @high @test_12
  Scenario: Style tag expression XSS
    Given kullanici oturum acmis
    When arama "<style>body{background:url('javascript:alert(1)')}</style>" ile yapilir
    Then expression kaldirulmali
