Feature: Visual Regression Testing
  As a QA engineer
  I want to detect visual regressions in the application
  So that I can ensure UI consistency across versions

  @visual
  Scenario: Capture and compare home page layout
    Given I am on the Paribu home page
    When I take a full page screenshot named "paribu-home-page"
    Then the visual comparison should pass

  @visual
  Scenario: Update home page baseline after design changes
    Given I am on the Paribu home page
    When I update the visual baseline "paribu-home-page"
    Then the visual baseline "paribu-home-page" should exist

  @visual
  Scenario: Compare featured markets section
    Given I am on the Paribu home page
    When I take a screenshot of ".featured-markets" named "featured-markets-section"
    Then the visual comparison should pass

  @visual
  Scenario: Detect minor visual differences
    Given I am on the Paribu home page
    When I take a full page screenshot named "paribu-home-detailed"
    Then the visual match should be above 85 percent

  @visual
  Scenario: Update element baseline after changes
    Given I am on the Paribu home page
    When I update the visual baseline for "[data-testid='featured-markets']" as "featured-markets-updated"
    Then the visual baseline "featured-markets-updated" should exist

  @visual
  Scenario: Compare market table layout
    Given I am on the Paribu home page
    When I go to markets page
    And I take a screenshot of "table" named "market-table"
    Then the visual comparison should pass

  @visual
  Scenario: Verify responsive design at different thresholds
    Given I am on the Paribu home page
    When I set visual threshold to 90
    And I take a full page screenshot named "paribu-responsive"
    Then the visual comparison should pass

  @visual
  Scenario: Compare login page button styling
    Given I navigate to Paribu login page
    When I take a screenshot of "button[type='submit']" named "login-button"
    Then the visual comparison should pass

  @visual
  Scenario: Clean up visual baselines
    Given the visual baseline "test-baseline-cleanup" does not exist
    When I am on the Paribu home page
    And I take a full page screenshot named "test-baseline-cleanup"
    And I wait 1 second
    When I delete the visual baseline "test-baseline-cleanup"
    Then the visual baseline "test-baseline-cleanup" should not exist

  @visual @critical
  Scenario: Compare critical UI components
    Given I am on the Paribu home page
    When I take a screenshot of "header" named "site-header"
    And I take a screenshot of "nav" named "site-navigation"
    And I take a screenshot of "footer" named "site-footer"
    Then the visual comparison should pass
