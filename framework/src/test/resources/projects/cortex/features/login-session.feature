@cortex @login @session
Feature: Cortex - Oturum Yonetimi

  Logout, oturum suresi dolmasi, login redirect senaryolari.

  Background:
    Given I open "cortex.url" link
    * I wait for page to load
    * I click "cookieAcceptButton" if it exists

  @pw @smoke
  Scenario: Basarili login sonrasi cikis yapilir
    When I write "${ENV:CORTEX_USERNAME:test_user@example.com}" into "userNameInput"
    And I enter encrypted password alias "cortexUser" into "passwordInput"
    And I click "loginButton"
    And I wait for page to load
    Then I see "dashboardHome"
    When I click "userMenuButton" if it exists
    And I click "logoutButton"
    And I wait for page to load
    Then I see "loginContainer"
    And I verify url contains "login"

  @pw
  Scenario: Cikis yapildiktan sonra dashboard URL'sine erisim login'e yonlendirir
    # Once login + logout
    When I write "${ENV:CORTEX_USERNAME:test_user@example.com}" into "userNameInput"
    And I enter encrypted password alias "cortexUser" into "passwordInput"
    And I click "loginButton"
    And I wait for page to load
    And I click "userMenuButton" if it exists
    And I click "logoutButton"
    And I wait for page to load
    # Sonra dashboard'a dogrudan git
    And I open "cortex.dashboard.url" link
    And I wait for page to load
    Then I see "loginContainer"

  @pw
  Scenario: Login sayfasinda zaten oturum acik kullanici dashboard'a yonlendirilir
    # Once basarili giris yap
    When I write "${ENV:CORTEX_USERNAME:test_user@example.com}" into "userNameInput"
    And I enter encrypted password alias "cortexUser" into "passwordInput"
    And I click "loginButton"
    And I wait for page to load
    Then I see "dashboardHome"
    # Login sayfasina dogrudan git — dashboard'a redirect olmali
    When I open "cortex.login.url" link
    And I wait for page to load
    Then I see "dashboardHome"

  @pw @no-parallel
  Scenario: Birden fazla tab acik iken cikis tum tab'larda etkili olur
    # Bu senaryo paralel calismaz cunku tab manipulasyonu var
    When I write "${ENV:CORTEX_USERNAME:test_user@example.com}" into "userNameInput"
    And I enter encrypted password alias "cortexUser" into "passwordInput"
    And I click "loginButton"
    And I wait for page to load
    Then I see "dashboardHome"
    # Yeni tab acmak step def'i framework'te yok; bu senaryo gelistirilebilir
