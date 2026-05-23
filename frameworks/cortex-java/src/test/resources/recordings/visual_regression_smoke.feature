# Auto-generated for E26 smoke
# Locator file: locators/yasin_retro_clean.json

Feature: visual_regression_smoke

  @recorded @cortex
  Scenario: Login sayfasının görsel baseline'ı oluşturulur
    Given I open the recorded url "https://cortex-test.bgtsai.com/login"
    Then visual snapshot matches "login-page-baseline"
