# Auto-generated for E27 smoke test
# Locator file: locators/yasin_retro_clean.json

Feature: a11y_smoke

  @recorded @cortex @a11y
  Scenario: Login sayfasının erişilebilirlik kontrolü
    Given I open the recorded url "https://cortex-test.bgtsai.com/login"
    Then page has no critical accessibility issues
