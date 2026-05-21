Feature: Website Navigation
  As a user
  I want to navigate through the website
  So that I can access different sections

  Scenario: Navigate to home page
    Given the application is started
    When I navigate to "https://paribu.com"
    Then page title should be "Paribu - Cryptocurrency Trading Platform"

  Scenario: Navigate to markets page
    Given I navigate to "https://paribu.com"
    When I click on "Markets"
    Then page URL should contain "market"
    And I should see a table with columns:
      | Market | Price | Change |

  Scenario: Go back in navigation
    Given I navigate to "https://paribu.com/market"
    When I click on "Trading"
    And I go back
    Then page URL should contain "market"

  Scenario: Search functionality
    Given I navigate to "https://paribu.com"
    When I search for "Bitcoin"
    Then I should see search results
    And page should contain "Bitcoin"

  @smoke
  Scenario: All main navigation links visible
    Given I navigate to "https://paribu.com"
    Then "a:has-text('Markets')" should be visible
    And "a:has-text('Trading')" should be visible
    And "a:has-text('Support')" should be visible
