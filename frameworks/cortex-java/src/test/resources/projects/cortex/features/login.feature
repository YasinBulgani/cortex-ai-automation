@cortex @login
Feature: Cortex - Giris Akisi (Happy Path)

  Cortex test ortamina basarili giris senaryolari.
  Tum senaryolar bagimsiz; her senaryo kendi BrowserContext'inde calisir (Playwright paralel).

  Background:
    Given I open "cortex.url" link
    * I wait for page to load
    * I click "cookieAcceptButton" if it exists

  @smoke @pw
  Scenario: Login sayfasi yuklenir ve gerekli elemanlar gorunur
    Then I see "loginContainer"
    And I see "userNameInput"
    And I see "passwordInput"
    And I see "loginButton"
    And I verify title contains "Cortex"

  @smoke @pw
  Scenario: Gecerli kullanici bilgileri ile basarili giris
    When I write "${ENV:CORTEX_USERNAME:test_user@example.com}" into "userNameInput"
    And I enter encrypted password alias "cortexUser" into "passwordInput"
    And I click "loginButton"
    And I wait for page to load
    Then I see "dashboardHome"
    And I verify url contains "dashboard"

  @pw
  Scenario: Enter tusuyla form gonderimi
    When I write "${ENV:CORTEX_USERNAME:test_user@example.com}" into "userNameInput"
    And I enter encrypted password alias "cortexUser" into "passwordInput"
    And I press "ENTER"
    And I wait for page to load
    Then I see "dashboardHome"

  @pw
  Scenario: "Beni hatirla" isaretlenince giris yapilir
    When I write "${ENV:CORTEX_USERNAME:test_user@example.com}" into "userNameInput"
    And I enter encrypted password alias "cortexUser" into "passwordInput"
    And I click "rememberMeCheckbox" if it exists
    And I click "loginButton"
    And I wait for page to load
    Then I see "dashboardHome"

  @pw
  Scenario: Login basarili olunca kullanici menusu gozukur
    When I write "${ENV:CORTEX_USERNAME:test_user@example.com}" into "userNameInput"
    And I enter encrypted password alias "cortexUser" into "passwordInput"
    And I click "loginButton"
    And I wait for page to load
    Then I see "dashboardHome"
    And I see "userMenu"
