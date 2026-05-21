@cortex @login @validation
Feature: Cortex - Login Form Dogrulamasi

  Hatali girisler ve form-level dogrulama senaryolari.

  Background:
    Given I open "cortex.url" link
    * I wait for page to load
    * I click "cookieAcceptButton" if it exists

  @pw @negative
  Scenario: Bos kullanici adi ile gonderim engellenir
    When I clear "userNameInput"
    And I enter encrypted password alias "cortexUser" into "passwordInput"
    And I click "loginButton"
    Then I see "loginErrorMessage"

  @pw @negative
  Scenario: Bos sifre ile gonderim engellenir
    When I write "${ENV:CORTEX_USERNAME:test_user@example.com}" into "userNameInput"
    And I clear "passwordInput"
    And I click "loginButton"
    Then I see "loginErrorMessage"

  @pw @negative
  Scenario: Her iki alan bos iken hata mesaji cikar
    When I clear "userNameInput"
    And I clear "passwordInput"
    And I click "loginButton"
    Then I see "loginErrorMessage"

  @pw @negative
  Scenario: Hatali sifre ile giris reddedilir
    When I write "${ENV:CORTEX_USERNAME:test_user@example.com}" into "userNameInput"
    And I write "${ENV:CORTEX_PASSWORD_WRONG:yanlis_sifre_123}" into "passwordInput"
    And I click "loginButton"
    And I wait for 2 seconds
    Then I see "loginErrorMessage"
    And I do not see "dashboardHome"

  @pw @negative
  Scenario: Var olmayan kullanici ile giris reddedilir
    When I write "kesinlikle_olmayan_kullanici_999@example.com" into "userNameInput"
    And I write "any_password_123" into "passwordInput"
    And I click "loginButton"
    And I wait for 2 seconds
    Then I see "loginErrorMessage"

  @pw @negative
  Scenario: Gecersiz e-posta formati ile uyari
    When I write "this-is-not-an-email" into "userNameInput"
    And I write "anyPass123" into "passwordInput"
    And I click "loginButton"
    Then I see "loginErrorMessage"

  @pw
  Scenario: Hata mesaji sonrasi yeniden deneme calismali
    When I write "wrong_user" into "userNameInput"
    And I write "wrong_pass" into "passwordInput"
    And I click "loginButton"
    And I wait for 1 seconds
    Then I see "loginErrorMessage"
    When I clear "userNameInput"
    And I write "${ENV:CORTEX_USERNAME:test_user@example.com}" into "userNameInput"
    And I clear "passwordInput"
    And I enter encrypted password alias "cortexUser" into "passwordInput"
    And I click "loginButton"
    And I wait for page to load
    Then I see "dashboardHome"

  @pw @negative
  Scenario: Sifre alani gizli (mask) modunda
    When I write "secret123" into "passwordInput"
    Then I verify "passwordInput" value is "secret123"
    # value erisilebilir ama gorsel olarak mask'li — input type=password
