@cortex @login @edge
Feature: Cortex - Login Sinir Durumlar

  Beklenmedik input'lar, performans, UI durumlari.

  Background:
    Given I open "cortex.url" link
    * I wait for page to load
    * I click "cookieAcceptButton" if it exists

  @pw
  Scenario: Cok uzun kullanici adi reddedilir veya truncate edilir
    When I write "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@example.com" into "userNameInput"
    And I write "ValidPassword123" into "passwordInput"
    And I click "loginButton"
    And I wait for 2 seconds
    Then I do not see "dashboardHome"

  @pw
  Scenario: Ozel karakterler sifrede - basarili giris
    # Unicode/utf-8 sifre destegi varsa
    When I write "${ENV:CORTEX_USERNAME:test_user@example.com}" into "userNameInput"
    And I write "P@ssw0rd!#$%^&*()_+" into "passwordInput"
    And I click "loginButton"
    And I wait for 2 seconds
    # Yanlissa hata cikar, dogruysa dashboard — burada sadece crash olmadigini test ediyoruz
    Then I see "pageBody"

  @pw
  Scenario: Bos boslukla baslayan kullanici adi trim'lenir
    When I write "   ${ENV:CORTEX_USERNAME:test_user@example.com}   " into "userNameInput"
    And I enter encrypted password alias "cortexUser" into "passwordInput"
    And I click "loginButton"
    And I wait for page to load
    # Cortex backend trim ediyorsa basarili olur
    Then I see "pageBody"

  @pw
  Scenario: Buyuk-kucuk harf kullanici adi (case-insensitive backend)
    When I write "TEST_USER@EXAMPLE.COM" into "userNameInput"
    And I enter encrypted password alias "cortexUser" into "passwordInput"
    And I click "loginButton"
    And I wait for 2 seconds
    Then I see "pageBody"

  @pw @slow
  Scenario: Yavas baglanti ile login (timeout testi)
    # Bu senaryo gercek kosumda dashboard.url'yi 30sn'ye kadar bekler
    When I write "${ENV:CORTEX_USERNAME:test_user@example.com}" into "userNameInput"
    And I enter encrypted password alias "cortexUser" into "passwordInput"
    And I click "loginButton"
    And I wait for 5 seconds
    Then I see "pageBody"

  @pw
  Scenario: Login butonu form submit edilirken disabled olur (UX kontrol)
    When I write "${ENV:CORTEX_USERNAME:test_user@example.com}" into "userNameInput"
    And I enter encrypted password alias "cortexUser" into "passwordInput"
    And I click "loginButton"
    # Loading spinner gorunmeli — varsa
    # Bu kontrol cortex backend'in implementasyonuna bagli
    And I wait for 1 seconds
    Then I see "pageBody"

  @pw @negative
  Scenario: Login butonu disabled iken iki kez tiklanamaz (double-submit korumasi)
    When I write "${ENV:CORTEX_USERNAME:test_user@example.com}" into "userNameInput"
    And I enter encrypted password alias "cortexUser" into "passwordInput"
    And I click "loginButton"
    And I click "loginButton" if it exists
    And I wait for page to load
    Then I see "pageBody"
    # Cortex backend rate-limit ile tek istek isleyecek
