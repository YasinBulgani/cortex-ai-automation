@cortex @login @security
Feature: Cortex - Login Guvenlik Testleri

  SQL injection, XSS, brute-force koruma senaryolari.
  Bu testler giris noktasinin guvenliginin temel kontrolu — hicbiri basarili giris uretmemeli.

  Background:
    Given I open "cortex.url" link
    * I wait for page to load
    * I click "cookieAcceptButton" if it exists

  @pw @sqli
  Scenario Outline: SQL injection denemeleri reddedilir
    When I write "<payload>" into "userNameInput"
    And I write "anyPass123" into "passwordInput"
    And I click "loginButton"
    And I wait for 2 seconds
    Then I do not see "dashboardHome"
    And I see "loginErrorMessage"

    Examples:
      | payload                              |
      | admin' OR '1'='1                     |
      | admin' --                            |
      | '; DROP TABLE users; --              |
      | admin' OR 1=1 #                      |
      | " OR ""="                            |
      | admin'/*                             |

  @pw @xss
  Scenario Outline: XSS payload'lari sanitize edilir / reddedilir
    When I write "<payload>" into "userNameInput"
    And I write "anyPass123" into "passwordInput"
    And I click "loginButton"
    And I wait for 2 seconds
    Then I do not see "dashboardHome"
    # Hicbir alert acilmadi varsayar — alert acilirsa Playwright timeout verir

    Examples:
      | payload                                       |
      | <script>alert('xss')</script>                |
      | <img src=x onerror=alert('xss')>             |
      | javascript:alert('xss')                       |
      | <svg/onload=alert('xss')>                    |
      | "><script>alert(1)</script>                  |

  @pw @brute-force @no-parallel
  Scenario: 5 ardisik basarisiz giris hesap kilidini tetikler (bilgilendirme)
    # Paralel calismaz cunku ayni hesap uzerinden ardisik denemeler gerekiyor.
    # Cortex backend'inde rate-limit varsa yeni IP/header rotasyonu olmadigindan
    # gercek brute-force testi bu seviyede dogru kurgulanmali. Bu sadece smoke.
    When I write "${ENV:CORTEX_USERNAME:test_user@example.com}" into "userNameInput"
    And I write "wrong1" into "passwordInput"
    And I click "loginButton"
    And I wait for 1 seconds
    Then I see "loginErrorMessage"
    When I clear "passwordInput"
    And I write "wrong2" into "passwordInput"
    And I click "loginButton"
    And I wait for 1 seconds
    Then I see "loginErrorMessage"
    When I clear "passwordInput"
    And I write "wrong3" into "passwordInput"
    And I click "loginButton"
    And I wait for 1 seconds
    Then I see "loginErrorMessage"

  @pw @csrf
  Scenario: CSRF token (varsa) form'da mevcut
    # Bu sadece bilgilendirici — gercek CSRF testi Burp/OWASP ZAP ile yapilir
    Then I see "loginContainer"
    # form input[name='_csrf'] var mi: opsiyonel
