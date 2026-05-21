@cortex @smoke @pw
Feature: Yeni senaryos

  Background:s
    Given I open "cortex.url" links
    * I wait for page to loads
    * I click "cookieAcceptButton" if it exists

  Scenario: Smoke check
    Then I see "loginContainer"
