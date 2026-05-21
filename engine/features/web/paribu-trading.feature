Feature: Paribu Cryptocurrency Trading
  As a trader
  I want to view crypto prices and make trading decisions
  So that I can buy and sell cryptocurrencies

  @smoke
  Scenario: View home page with featured markets
    Given I am on the Paribu home page
    Then featured markets should be visible
    And featured markets should contain at least 10 cryptocurrencies

  Scenario Outline: Search for cryptocurrencies
    Given I am on the Paribu home page
    When I search for "<crypto>"
    Then search results should show "<crypto>"

    Examples:
      | crypto |
      | Bitcoin |
      | Ethereum |
      | Cardano |

  @smoke
  Scenario: Navigate to markets
    Given I am on the Paribu home page
    When I go to markets page
    Then market table should be visible
    And market should have 50 or more cryptocurrencies

  Scenario: View market prices
    Given I am on the Paribu home page
    When I view the markets
    And I get the price for "Bitcoin"
    Then the price should be available

  @critical
  Scenario: User login workflow
    Given I navigate to Paribu login page
    When I login with "test@example.com" and "TestPassword123!"
    Then login should be successful

  Scenario: Login with invalid credentials
    Given I navigate to Paribu login page
    When I login with "invalid@example.com" and "WrongPassword"
    Then login error message should appear
    And page URL should contain "login"

  Scenario: User profile access
    Given I am logged in as "test@example.com"
    When I go to my profile
    Then profile information should be displayed

  @critical
  Scenario: User logout
    Given I am logged in as "test@example.com"
    When I logout
    Then I should be logged out

  Scenario: See featured Bitcoin
    Given I am on the Paribu home page
    Then I should see "BTC" in featured markets
