Feature: Complete User Journey - Integration Testing
  As a user
  I want to complete full workflows in the application
  So that I can verify end-to-end functionality

  @e2e @critical
  Scenario: Complete trading workflow with validation
    Given I am on the Paribu home page
    When I measure the page load time
    Then the page load time should be less than 5000 milliseconds
    When I check the core web vitals
    Then the core web vitals should be good
    When I take a full page screenshot named "paribu-home"
    Then the visual comparison should pass
    When featured markets should be visible
    And featured markets should contain at least 10 cryptocurrencies
    When I go to markets page
    And I measure the page load time
    Then the page load time should be less than 4000 milliseconds
    When I check the network performance
    Then the total network requests should be less than 60
    When I take a full page screenshot named "market-page"
    Then the visual comparison should pass

  @e2e @accessibility
  Scenario: Accessibility compliance across pages
    Given I am on the Paribu home page
    When I run accessibility scan
    Then there should be no critical accessibility violations
    When I go to markets page
    And I run accessibility scan
    Then there should be no critical accessibility violations
    When I navigate to Paribu login page
    And I run accessibility scan
    Then there should be no critical accessibility violations

  @e2e @smoke
  Scenario: Authentication workflow with performance validation
    Given I navigate to Paribu login page
    When I measure the page load time
    Then the page load time should be less than 3000 milliseconds
    When I have random test data from "users"
    And I login with email and password from test data
    Then login should be successful
    When I check the core web vitals
    Then the core web vitals should be good
    When I go to my profile
    Then profile information should be displayed

  @e2e @visual @performance
  Scenario: Search functionality with multi-metric validation
    Given I am on the Paribu home page
    When I take a full page screenshot named "search-initial"
    And I search for "Bitcoin"
    Then search results should show "Bitcoin"
    When I measure the page load time
    Then the first contentful paint should be less than 2000 milliseconds
    And the cumulative layout shift should be less than 0.15
    When I take a full page screenshot named "search-results"
    Then the visual comparison should pass

  @e2e @data-driven
  Scenario: Multi-user authentication testing
    Given I have 3 unique test data items from "users"
    When I navigate to Paribu login page
    And I login with email and password from test data
    Then login should be successful
    When I go to my profile
    Then profile information should be displayed
    And I logout
    Then I should be logged out

  @e2e @critical @accessibility
  Scenario: Complete navigation with accessibility and performance checks
    Given I am on the Paribu home page
    When I run accessibility scan
    And I measure the page load time
    And I take a full page screenshot named "home-complete"
    Then there should be no serious accessibility violations
    And the page load time should be less than 5000 milliseconds
    And the visual comparison should pass
    When I go to markets page
    And I run accessibility scan
    And I measure the page load time
    And I take a full page screenshot named "markets-complete"
    Then there should be no serious accessibility violations
    And the page load time should be less than 4000 milliseconds
    And the visual comparison should pass

  @e2e @visual-regression
  Scenario: UI consistency across multiple pages
    Given I am on the Paribu home page
    When I take a screenshot of "header" named "header-home"
    And I take a screenshot of "footer" named "footer-home"
    Then the visual comparison should pass
    When I go to markets page
    And I take a screenshot of "header" named "header-markets"
    And I take a screenshot of "footer" named "footer-markets"
    Then the visual comparison should pass

  @e2e @performance-critical
  Scenario: Performance benchmark across critical paths
    Given I am on the Paribu home page
    When I measure the page load time
    Then the page load time should be less than 4000 milliseconds
    And the DOM content should load in less than 3000 milliseconds
    And the first contentful paint should be less than 2000 milliseconds
    And the largest contentful paint should be less than 3000 milliseconds
    And the cumulative layout shift should be less than 0.15
    When I go to markets page
    And I measure the page load time
    Then the page load time should be less than 4000 milliseconds
    And the first contentful paint should be less than 2000 milliseconds

  @e2e @integration
  Scenario: Full workflow with data management
    Given I have generated test data with 5 users
    And I navigate to Paribu login page
    When I have random test data from "users"
    And I login with email and password from test data
    Then login should be successful
    When I measure the page load time
    And I run accessibility scan
    And I check the core web vitals
    Then the page load time should be less than 3000 milliseconds
    And the core web vitals should be good

  @e2e @critical @comprehensive
  Scenario: Comprehensive pre-release validation
    # Home Page
    Given I am on the Paribu home page
    When I measure the page load time
    And I check the core web vitals
    And I run accessibility scan
    And I take a full page screenshot named "home-release"
    Then the page load time should be less than 5000 milliseconds
    And the core web vitals should be good
    And there should be no critical accessibility violations
    And the visual comparison should pass

    # Markets Page
    When I go to markets page
    And I measure the page load time
    And I run accessibility scan
    And I check the network performance
    And I take a full page screenshot named "markets-release"
    Then the page load time should be less than 4000 milliseconds
    And there should be no critical accessibility violations
    And the total network requests should be less than 60
    And the visual comparison should pass

    # Login Page
    When I navigate to Paribu login page
    And I run accessibility scan
    And I measure the page load time
    Then there should be no critical accessibility violations
    And the page load time should be less than 3000 milliseconds
