Feature: Data-Driven End-to-End Workflows
  As a test engineer
  I want to execute data-driven E2E tests with multiple validation layers
  So that I can verify application behavior with realistic test data

  @e2e @data-driven
  Scenario: Login and navigate with generated test data
    Given I have generated test data with 3 users
    And I navigate to Paribu login page
    When I measure the page load time
    Then the page load time should be less than 3000 milliseconds
    When I have random test data from generated data
    And I login with email and password from test data
    Then login should be successful

  @e2e @data-driven @performance
  Scenario: Multiple user registration attempts with performance tracking
    Given I have generated test data with 5 users
    When I navigate to Paribu login page
    And I measure the page load time
    And I check the core web vitals
    Then the page load time should be less than 3500 milliseconds
    And the core web vitals should be good

  @e2e @data-driven @accessibility
  Scenario: Data-driven accessibility testing
    Given I am on the Paribu home page
    When I measure the page load time
    And I run accessibility scan
    And I have test data from "users"
    Then there should be no critical accessibility violations
    And the page load time should be less than 5000 milliseconds

  @e2e @data-driven @visual
  Scenario: Visual consistency with data variations
    Given I have generated test data with 2 users
    When I am on the Paribu home page
    And I take a full page screenshot named "home-baseline"
    Then the visual comparison should pass

  @e2e @data-driven @critical
  Scenario: Complete transaction simulation with data management
    Given I have generated test data with 1 users
    And I navigate to Paribu login page
    When I measure the page load time
    And I have random test data from "users"
    And I login with email and password from test data
    Then login should be successful
    When I go to markets page
    And I measure the page load time
    And I check the core web vitals
    Then the page load time should be less than 4000 milliseconds
    And the core web vitals should be good

  @e2e @data-driven
  Scenario: Search with multiple test data items
    Given I have 3 unique test data items from "users"
    And I am on the Paribu home page
    When I search for "Bitcoin"
    Then search results should show "Bitcoin"
    When I measure the page load time
    Then the page load time should be less than 4000 milliseconds

  @e2e @data-driven @integration
  Scenario: Multi-step workflow with data transformation
    Given I have test data from "users"
    When I extract fields "email, username" from test data
    And I navigate to Paribu login page
    Then featured markets should contain at least 1 cryptocurrencies

  @e2e @data-driven @smoke
  Scenario: Basic E2E with all validation layers
    Given I have generated test data with 1 users
    And I am on the Paribu home page
    When I measure the page load time
    And I run accessibility scan
    And I take a full page screenshot named "smoke-e2e"
    Then the page load time should be less than 5000 milliseconds
    And there should be no critical accessibility violations
    And the visual comparison should pass

  @e2e @data-driven @performance @critical
  Scenario: High-load performance simulation
    Given I have generated test data with 10 users
    And I am on the Paribu home page
    When I check the core web vitals
    And I measure the page load time
    And I check the network performance
    Then the core web vitals should be good
    And the page load time should be less than 5000 milliseconds
    And the total network requests should be less than 60

  @e2e @data-driven @comprehensive
  Scenario: Comprehensive multi-metric validation workflow
    Given I have comprehensive test context
    And I am on the Paribu home page
    When I measure the page load time
    And I run accessibility scan
    And I take a full page screenshot named "comprehensive-e2e"
    And I check the core web vitals
    And I check the network performance
    Then there should be no serious accessibility violations
    And the page load time should be less than 5000 milliseconds
    And the core web vitals should be good
    And the visual comparison should pass
    And the total network requests should be less than 60
