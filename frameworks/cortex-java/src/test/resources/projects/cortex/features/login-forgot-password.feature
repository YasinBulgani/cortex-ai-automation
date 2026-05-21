@cortex @login @forgot-password
Feature: Cortex - Sifremi Unuttum Akisi

  Sifre sifirlama akisinin temel UI testleri.

  Background:
    Given I open "cortex.url" link
    * I wait for page to load
    * I click "cookieAcceptButton" if it exists

  @pw @smoke
  Scenario: "Sifremi Unuttum" linki gorunur
    Then I see "forgotPasswordLink"

  @pw
  Scenario: Link tiklaninca sifre sifirlama sayfasina yonlendirir
    When I click "forgotPasswordLink"
    And I wait for page to load
    Then I verify url contains "forgot"
    # veya "reset" - cortex implementasyonuna bagli

  @pw
  Scenario: Sifirlama formu gerekli alanlari icerir
    When I click "forgotPasswordLink"
    And I wait for page to load
    Then I see "resetEmailInput"
    And I see "resetSubmitButton"

  @pw
  Scenario: Gecerli e-posta ile sifirlama istegi gonderilir
    When I click "forgotPasswordLink"
    And I wait for page to load
    And I write "${ENV:CORTEX_USERNAME:test_user@example.com}" into "resetEmailInput"
    And I click "resetSubmitButton"
    And I wait for 2 seconds
    Then I see "resetSuccessMessage"

  @pw @negative
  Scenario: Gecersiz format e-posta ile sifirlama reddedilir
    When I click "forgotPasswordLink"
    And I wait for page to load
    And I write "not-an-email" into "resetEmailInput"
    And I click "resetSubmitButton"
    Then I do not see "resetSuccessMessage"

  @pw @negative
  Scenario: Bos e-posta ile sifirlama reddedilir
    When I click "forgotPasswordLink"
    And I wait for page to load
    And I clear "resetEmailInput"
    And I click "resetSubmitButton"
    Then I do not see "resetSuccessMessage"
